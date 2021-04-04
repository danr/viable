from __future__ import annotations
from dataclasses import *
from typing import *

import bottle
from bottle import route, get, static_file
from bottle.ext.websocket import GeventWebSocketServer, websocket
from geventwebsocket.exceptions import WebSocketError

import atexit
import threading
import json
import os
import socket
import subprocess
import sys

def oneliner(raw_msg: bytes) -> bytes:
    '''
    Return a copy of the message with only a newline at the end,
    reformatting its json if necessary.
    '''
    raw_msg = raw_msg.strip()
    if b'\n' in raw_msg:
        raw_msg = json.dumps(json.loads(raw_msg.decode())).encode()
        assert b'\n' not in raw_msg
    return raw_msg + b'\n'

def spawn(f: Callable[[], None]) -> None:
    threading.Thread(target=f, daemon=True).start()

def bridge(sockfile='.brbr') -> [dict[str, Callable], Callable[[Any], None]]:
    s = socket.socket(socket.AF_UNIX)
    s.connect(sockfile) # for now you need to start it manually

    cbs: dict[str, Callable] = {}

    # forward msgs on unix socket to exposed python function handlers
    def on_msg(msg_raw: bytes) -> None:
        try:
            msg = json.loads(msg_raw)
        except ValueError:
            msg = None
        if isinstance(msg, dict):
            if msg.get('type') == 'call':
                print(f"Calling: {msg!r}")
                cb = cbs.get(msg['name'])
                if cb:
                    cb(*msg.get('args', []), **msg.get('kwargs', {}))
                    return
        print(f'Unhandled: {msg_raw!r}')

    spawn(lambda: socket_msg_handler(s, on_msg))

    return cbs, lambda msg: s.sendall(json.dumps(msg).encode() + b'\n')

def socket_msg_handler(conn: socket.socket, on_msg: Callable[[bytes], None]) -> None:
    data = b''
    while True:
        while b'\n' not in data:
            recv = conn.recv(4096)
            data += recv
            if not recv:
                return
        msgs = data.splitlines(True)
        if not msgs[-1].endswith(b'\n'):
            data = msgs.pop()
        else:
            data = b''
        for msg in msgs:
            on_msg(msg[:-1])

@dataclass
class State:
    conn: socket.socket | None = None
    ws: websocket | None = None

state = State()

def serve(sockfile='.brbr', port=8234, host='127.0.0.1', start_browser=True) -> None:
    atexit.register(lambda: os.remove(sockfile))
    print(sockfile)
    with socket.socket(socket.AF_UNIX) as s:
        s.bind(sockfile)
        s.listen(1)

        @spawn
        def start_bottle() -> None:
            print('starting bottle...')
            bottle.run(host=host, port=port, debug=True, server=GeventWebSocketServer)

        if start_browser:
            subprocess.run(f'''
                chromium --app=http://localhost:{port} --auto-open-devtools-for-tabs & disown
            ''', shell=True)

        while True:
            conn, _ = s.accept()
            with conn:
                # forward msgs on unix socket to web socket
                state.conn = conn
                def on_msg(msg):
                    if ws := state.ws:
                        ws.send(msg.decode())
                socket_msg_handler(conn, on_msg)
            state.conn = None


@route('/ws', apply=[websocket])
def handle_ws(ws: websocket) -> None:
    print(f"handle_ws: got websocket, putting on queue...")
    if state.ws is not None:
        if state.conn:
            print(f"Websocket already paired with unix socket, skipping this one...")
            return
        else:
            print(f"Changing to new websocket")
            return
    state.ws = ws
    while True:
        try:
            msg_raw = ws.receive()
        except WebSocketError as e:
            print(str(e))
            break
        if msg_raw is None:
            print('Received None on websocket')
            break
        # print(f"Received: {msg_raw!r}")
        msg_raw = oneliner(msg_raw.encode())
        # print(f"Sending: {msg_raw!r}")
        if conn := state.conn:
            conn.sendall(msg_raw)
    if conn := state.conn:
        print('websocket closed so closing unix socket')
        state.conn = None
        conn.close()
    state.ws = None

@get('/')
@get('/index.html')
def root() -> None:
    return static_file('index.html', root='.')

if '--serve' in sys.argv:
    serve()

