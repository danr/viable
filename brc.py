from __future__ import annotations
from dataclasses import *
from typing import *
import inspect

from browserbridge import low_level_client
import json
from datetime import datetime

class JS():
    '''
    Call an exposed javascript function.
    '''
    def __init__(self, ws_send):
        self.ws_send = ws_send

    def call(self, name, *args, **kws):
        args = list(args)
        if kws:
            args += [kws]
        msg = dict(
            type='call',
            name=name,
            args=args,
        )
        self.ws_send(msg)

    def __getattr__(self, name):
        if name in ('shape', 'dtype'):
            raise AttributeError()
        return lambda *args, **kws: self.call(name, *args, **kws)

    def __call__(self, selector):
        return JSSelector(self, selector)

class JSSelector():
    '''
    This is so you can use = on a selected value. Example:

        js('#foo').html = '<div>more markup</div>'
    '''
    def __init__(self, js, selector):
        self.js = js
        self.selector = selector

    def __getattr__(self, attr):
        if attr in ('shape', 'dtype'):
            raise AttributeError()
        elif attr in ('js', 'selector'):
            return self.__dict__[attr]
        return JSSelectorAttr(self.js, self.selector, attr)

    def __setattr__(self, attr, value):
        if attr in ('js', 'selector'):
            self.__dict__[attr] = value
        elif isinstance(value, JSSelectorAttr):
            # already handled by +=, skip
            return
        elif attr in ('outerHTML'):
            self.js.set_prop(self.selector, 'outerHTML', value)
        elif attr in ('html', 'innerHTML'):
            self.js.set_prop(self.selector, 'innerHTML', value)
        elif 1:
            attr = 'className' if attr == 'cls' else attr
            self.js.set_attr(self.selector, attr, value)
        else:
            raise ValueError('Unsupported attr:' + attr)

class JSSelectorAttr():
    '''
    This is so you can use += on a selected value. Example:

        js('#foo').html += '<div>more markup</div>'
    '''
    def __init__(self, js, selector, attr):
        self.js = js
        self.selector = selector
        self.attr = attr

    def __iadd__(self, value):
        if self.attr in ('outerHTML'):
            self.js.add_prop(self.selector, 'outerHTML', value)
            return self
        if self.attr in ('html', 'innerHTML'):
            self.js.add_prop(self.selector, 'innerHTML', value)
            return self
        else:
            attr = self.attr
            attr = 'className' if attr == 'cls' else attr
            self.js.add_attr(self.selector, attr, value)
            return self

@dataclass(frozen=True)
class Py:
    cbs: dict[str, Callable]

    def expose(self, f, name=None):
        name = name or f.__name__
        self.cbs[name] = f
        # print('Exposed', name)
        return f

    def handler(self, f):
        args = []
        for param in inspect.signature(f).parameters.values():
            if param.kind != param.POSITIONAL_OR_KEYWORD:
                raise ValueError('Only positional or keyword params supported')
            head, *tail = param.name.split('_', 1)
            if head in ['target', 'currentTarget']:
                args += [f'event.{head}?.{tail[0]}']
            else:
                args += [f'event.{param.name}']
        name = hex(id(f))
        self.expose(f, name)
        args = ', '.join(args)
        return f'pycall({name!r}, [{args}])'

def client():
    cbs, ws_send = low_level_client()

    js = JS(ws_send)
    py = Py(cbs)

    js.raw_eval('''
      expose(function set_prop(sel, prop, value) { document.querySelector(sel)[prop] = value })
      expose(function set_attr(sel, attr, value) { document.querySelector(sel).setAttribute(attr, value) })
      expose(function add_prop(sel, prop, value) { document.querySelector(sel)[prop] += value })
      expose(function add_attr(sel, attr, value) { const e = document.querySelector(sel); e.setAttribute(attr, e.getAttribute(attr) + value) })
    ''')

    return js, py

# utils

A = TypeVar('A')

from show import pr, show

def b64(data, mime=None):
    import io
    import base64
    if isinstance(data, io.BytesIO):
        data = data.getvalue()
    if isinstance(data, str):
        data = data.encode()
    data = base64.b64encode(data).decode()
    if mime:
        return f'data:{mime};base64,{data}'
    else:
        return data

def b64png(data):
    return b64(data, mime='image/png')

def b64svg(data):
    return b64(data, mime='image/svg+xml')

def b64jpg(data):
    return b64(data, mime='image/jpeg')

def b64gif(data):
    return b64(data, mime='image/gif')

