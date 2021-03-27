from bottle import route, get, run, static_file
from bottle import request, Bottle, abort
from bottle.ext.websocket import GeventWebSocketServer, websocket
from geventwebsocket.exceptions import WebSocketError
from queue import SimpleQueue
import threading
import json

class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

store = globals().get('store', dotdict())
store.reloads = store.reloads or 0
store.reloads += 1

class Cell:
    def __init__(initial=None):
        self.value = initial
        self.cv = threading.Condition()

    def put(self, value):
        with self.cv:
            self.value = value
            self.cv.notify_all()

    def get(self):
        with self.cv:
            value, = self.wait_for(lambda: 0 if self.value is None else [self.value])
            return value

def spawn(f):
    threading.Thread(target=f, daemon=True).start()

PORT = 8234
HOST = '127.0.0.1'

def start_bottle():

    ws_queue = SimpleQueue()

    def pop_ws():
        return ws_queue.get()

    @route('/ws', apply=[websocket])
    def handle_ws(ws):
        print(f"handle_ws: got websocket, putting on queue...")
        reply_chan = SimpleQueue()
        ws_queue.put((ws, reply_chan))
        cbs, onclose = reply_chan.get()
        while True:
            try:
                msg_raw = ws.receive()
            except WebSocketError as e:
                print(str(e))
                break
            if not msg_raw:
                break
            try:
                msg = json.loads(msg_raw)
            except ValueError:
                msg = None
            if isinstance(msg, dict):
                if msg.get('type') == 'call':
                    print(f"{store.reloads} Calling: {msg!r}")
                    cbs[msg['name']](*msg.get('args', []), **msg.get('kwargs', {}))
            else:
                print(f"{store.reloads} Received: {msg or msg_raw!r}")
        onclose and onclose()

    @get('/')
    @get('/index.html')
    def root():
        return static_file('index.html', root='.')

    # store.bottle_init = False
    if not store.bottle_init:
        store.bottle_init = True
        @spawn
        def main():
            print('running main')
            run(host=HOST, port=PORT, debug=True, server=GeventWebSocketServer)

    return dotdict(pop_ws=pop_ws)

def get_bottle():
    if not store.bottle:
        store.bottle = start_bottle()
    return store.bottle

def get_connection(cbs, onclose=None):
    ws, reply_chan = get_bottle().pop_ws()
    reply_chan.put([cbs, onclose])
    return ws

def connection(cbs, start_browser=True):
    if start_browser and not store.browser_init:
        import subprocess
        store.browser_init = True
        subprocess.Popen(f'chromium --app=http://localhost:{PORT} --auto-open-devtools-for-tabs & disown', shell=True)
    if not store.ws:
        store.ws = get_connection(cbs, onclose=lambda: delattr(store, 'ws'))
    return store.ws

def serve(h):
    while True:
        cbs = {}
        ws = get_connection(cbs)
        spawn(lambda: h(cbs, ws))

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

