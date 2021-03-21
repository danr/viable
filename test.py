from bottle import route, get, run, static_file
from bottle import request, Bottle, abort
from bottle.ext.websocket import GeventWebSocketServer, websocket
from geventwebsocket.exceptions import WebSocketError
from queue import Queue
import threading
import json

PORT = 8234
HOST = '127.0.0.1'

class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

store = globals().get('store', dotdict())
store.reloads = store.reloads or 0
store.reloads += 1
store.exposed = store.exposed or {}

@route('/ws', apply=[websocket])
def handle_ws(ws):
    print(f"handle_ws")
    if store.ws:
        print(f"closing old ws")
        store.ws.close()
    store.ws = ws
    print(f"Got websocket!")
    while True:
        try:
            message = ws.receive()
            if not message:
                break
            print(f"{store.reloads} Your message was: {message!r}")
        except WebSocketError as e:
            print(str(e))
            break

@get('/')
@get('/index.html')
def root():
    return static_file('index.html', root='.')

# store.bottle_init = False
if not store.bottle_init:
    store.bottle_init = True
    def main():
        run(host=HOST, port=PORT, debug=True, server=GeventWebSocketServer)
    print('running main')
    thread = threading.Thread(target=main, daemon=True)
    thread.start()

if not store.browser_init:
    import subprocess
    store.browser_init = True
    subprocess.Popen(f'chromium --app=http://localhost:{PORT} --auto-open-devtools-for-tabs & disown', shell=True)

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
                self.ws.send(msg)
            else:
                raise RuntimeError('No websocket in self')
        return call

    def __call__(self, selector):
        return JSSelector(self, selector)

import snoop

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
        if self.attr in ('html', 'innerHTML'):
            self.js.add_prop(self.selector, 'innerHTML', value)
            return self
        else:
            attr = self.attr
            attr = 'className' if attr == 'cls' else attr
            self.js.add_attr(self.selector, attr, value)
            return self


js = JS(store.ws)

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

js('body').html = '''
  <h1>Major</h1>
  <div id=major></div>
  <h2>Minor</h1>
  <div id=minor></div>
'''

js('#major').html = 'lol #' + str(store.reloads)
js('#major').style = 'color:#99c; font-family: monospace; font-size: 5em;'
js('#major').onclick = 'console.log(this, event)'

js('#minor').html = 'lol #' + str(store.reloads)
js('#minor').style = 'color:#9c9; font-family: monospace; font-size: 5em;'
js('#minor').onclick = 'console.log(this, event)'

js('#minor').html += ' also this!'
js('#minor').html += ' and this!'
js('#minor').style += 'transform: rotate(-3deg);'

if 0:
    x = 0
    while x < 3e6:
        x += 1
        if x % 1e5 == 0:
            print(x)
            js.html(f'<pre>x: {x}</pre>')

