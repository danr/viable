import asyncio
# stop using asyncio
# use gevent+greenlet stuff instead
# and bottle
import threading

store.port = 8234
store.host = '127.0.0.1'
store.root = r'''
<!DOCTYPE html>
<html>
<head>
  <script type="text/javascript">
    'use strict'
    const ws = new WebSocket("ws://localhost:8234/ws")
    ws.onopen = function() {
        ws.send("Hello, world")
    }
    ws.onmessage = function (e) {
        try {
            const msg = JSON.parse(e.data)
            if (msg.type == 'eval') {
                const scope = msg.scope || {}
                const names = Object.keys(scope)
                const body = [
                    "'use strict'",
                    ...names.map(name => "let " + name + " = this." + name),
                    msg.body,
                ].join('\n')
                console.log(body)
                console.log(scope)
                const f = Function(body).bind(scope)
                f()
            } else {
                console.log(e.data)
            }
        } catch (e) {
            console.log(e.data)
            console.error(e)
        }
    }
    window.ws = ws
  </script>
</head>
<body style="background: #333; color: #eee;">hello?'
</body>
</html>
'''

from bottle import route, run

@route('/')
def hello():
    return store.root

from bottle import request, Bottle, abort
from bottle.ext.websocket import GeventWebSocketServer, websocket
from geventwebsocket.exceptions import WebSocketError
import json
from queue import Queue

store.reloads = store.reloads or 0
store.reloads += 1
store.inbox = store.inbox or Queue()

@route('/ws', apply=[websocket])
def handle_ws(ws):
    if store.ws:
        store.ws.close()
    store.ws = ws
    while True:
        try:
            message = ws.receive()
            if not message:
                break
            print(f"{store.reloads} Your message was: {message!r}")
            store.inbox.put_nowait(message)
        except WebSocketError as e:
            print(str(e))
            break

# store.bottle_init = False
if not store.bottle_init:
    store.bottle_init = True
    main = lambda:  run(host=store.host, port=store.port, debug=True, server=GeventWebSocketServer)
    print('running main')
    thread = threading.Thread(target=main, daemon=True)
    thread.start()

if not store.browser_init:
    import subprocess
    store.browser_init = True
    subprocess.Popen(f'chromium --app=http://localhost:{store.port} --auto-open-devtools-for-tabs & disown', shell=True)

try:
    lol += 1
except NameError:
    lol = 1

print(f'{lol=}')

store.root += ' ' + str(lol)

def ws_eval(body, **scope):
    if store.ws:
        store.ws.send(json.dumps(dict(
            type='eval',
            body=body,
            scope=scope,
        )))
    else:
        raise RuntimeError('No websocket in store')

ws_eval('console.log(reloads)', reloads=store.reloads)

ws_eval('document.body.innerHTML = root', root=store.root)

ws_eval('ws.send("helllo?")')

def spawn_listener():
    '''
    Listeners can be spawned in their own threads
    '''
    def listener():
        while True:
            msg = store.inbox.get()
            print(threading.get_ident(), 'message:', msg)

    thread = threading.Thread(target=listener, daemon=True)
    thread.start()

# while True:
#     try:
#         message = ws.receive()
#         ws.send(f"{store.reloads} Your message was: {message!r}")
#         ws.send(json.dumps({'foo':list(range(10))}))
#         print(f"{store.reloads} Your message was: {message!r}")
#     except WebSocketError as e:
#         print(str(e))
#         break

# print(help(exec))

# flags.clear = True
# flags.debug = False

store.x = store.x or 0
while True:
    store.x += 1
    if store.x % 1e5 == 0:
        print(store.x)
        ws_eval('document.body.innerHTML = html', html=f'<pre>x: {store.x}</pre>')

