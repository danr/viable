import show
import snoop
snoop.install(pformat=show.show)

from browserbridge import connection, b64png, dotdict
import json

store = globals().get('store', dotdict())
store.reloads = store.reloads or 0
store.reloads += 1
store.exposed = store.exposed or {}
pp(store.exposed)
store.exposed.clear()
pp(store.exposed)

def expose(f, name=None):
    name = name or f.__name__
    store.exposed[name] = f
    print('Exposed', name)
    return f

class JS():
    '''
    Call an exposed javascript function.
    '''
    def __init__(self, ws):
        self.ws = ws

    def __getattr__(self, name):
        if name in ('shape', 'dtype'):
            raise AttributeError()
        def call(*args, **kws):
            if self.ws:
                args = list(args)
                if kws:
                    args += [kws]
                msg = dict(
                    type='call',
                    name=name,
                    args=args,
                )
                msg = json.dumps(msg)
                try:
                    self.ws.send(msg)
                except Exception as e:
                    print('Websocket dead?', str(e))
                    self.ws = None
            else:
                print('No websocket in self')
        return call

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

ws = connection(store.exposed)

js = JS(ws)

js.raw_eval('''
    console.log(reloads)
    ws.send("Reloads: " + reloads)
''', reloads=store.reloads)

js.raw_eval('''
  expose(function set_prop(sel, prop, value) { document.querySelector(sel)[prop] = value })
  expose(function set_attr(sel, attr, value) { document.querySelector(sel).setAttribute(attr, value) })
  expose(function add_prop(sel, prop, value) { document.querySelector(sel)[prop] += value })
  expose(function add_attr(sel, attr, value) { const e = document.querySelector(sel); e.setAttribute(attr, e.getAttribute(attr) + value) })
''')

@expose
def reply(*args, **kws):
    value = kws.get('value')
    if value:
        js('#minor').html = str(value)
    else:
        print('reply', args, kws)

import inspect
def handler(f):
    args = []
    for param in inspect.signature(f).parameters.values():
        if param.kind != param.POSITIONAL_OR_KEYWORD:
            raise ValueError('Only positional or keyword params supported')
        head, *tail = param.name.split('_', 1)
        if head in ['target', 'currentTarget']:
            args += [f'event?.{head}.{tail[0]}']
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
    setattr(js('#minor'), 'html', pp(target_value)),
    js('#footer').outerHTML.__iadd__(f'<pre>{pp(target_value)}</pre>'),
])

js('#minor').html = 'lol #' + str(store.reloads)
js('#minor').style = 'color:#9c9; font-family: monospace; font-size: 5em;'
js('#minor').onclick = handler(lambda x, y: pp(x, y))
# js('#minor').onclick = "pycall('reply', [event.x, event.y])"

js('#minor').html += ' also this!'
js('#minor').html += ' and this!'
js('#minor').style += 'transform: rotate(-3deg);'

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

