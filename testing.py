from __future__ import annotations
from dataclasses import *
from typing import *

import show
import snoop
snoop.install(pformat=show.show)
pp: Any

from browserbridge import bridge
import json
from datetime import datetime

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

cbs, ws_send = bridge()

def expose(f, name=None):
    name = name or f.__name__
    cbs[name] = f
    print('Exposed', name)
    return f

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

js = JS(ws_send)

js.raw_eval('''
    console.log("Reload: " + now)
    ws.send(JSON.stringify('Reload: ' + now))
''', now=now)

js.raw_eval('''
  expose(function set_prop(sel, prop, value) { document.querySelector(sel)[prop] = value })
  expose(function set_attr(sel, attr, value) { document.querySelector(sel).setAttribute(attr, value) })
  expose(function add_prop(sel, prop, value) { document.querySelector(sel)[prop] += value })
  expose(function add_attr(sel, attr, value) { const e = document.querySelector(sel); e.setAttribute(attr, e.getAttribute(attr) + value) })
''')

import inspect
def handler(f):
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
    expose(f, name)
    args = ', '.join(args)
    return f'pycall({name!r}, [{args}])'

js('body').html = '''
  <h1>Major</h1>
  <div id=major></div>
  <h2>Minor</h1>
  <img id=plot />
  <div id=minor></div>
  <div id=counter></div>
  <div id=footer></div>
'''

js('#major').style = 'color:#99c; font-family: monospace; font-size: 5em;'
js('#major').outerHTML = '<input id=txt type=text />'
js('#txt').oninput = handler(lambda target_value: [
    js('#minor').__setattr__('html', pp(target_value)),
    js('#footer').outerHTML.__iadd__(f'<pre>{pp(target_value)}</pre>'),
])

js('#minor').html = 'lol #' + now
js('#minor').style = 'color:#9c9; font-family: monospace; font-size: 5em;'
js('#minor').onclick = handler(lambda x, y: pp(x, y))

js('#minor').html += ' also this!'
js('#minor').html += ' and this!'
js('#minor').style += 'transform: rotate(-3deg);'

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


import seaborn as sns
p=sns.scatterplot(x=[0, 2, 3, 4], y=[1, 2, 3, 2])
# pp(repr(p.figure), dir(p.figure))
# pp(p.figure.savefig)
import io
buf = io.BytesIO()
p.figure.savefig(buf, format='png')
import base64
js('#plot').src = b64png(buf)

while True:
    x = 0
    while x < 3e6:
        x += 1
        if x % 1e5 == 0:
            print(x)
            js('#counter').html = f'<pre>x: {x}</pre>'

