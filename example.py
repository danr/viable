from __future__ import annotations
from typing import Iterator, Any, cast

from flask import request
from viable import serve, esc, div, pre, Node, js
from viable.provenance import store, Var
import viable as V

from pprint import pformat, pprint

serve.suppress_flask_logging()

from datetime import datetime
server_start = datetime.now()
last_msg = ''
request_count = 0

@serve.expose
def example_exposed(*args: str):
    print(args)
    global last_msg
    last_msg = ' '.join([*args, cast(Any, request).headers['User-Agent']])

def input(store: dict[str, str | bool], name: str, type: str, value: str | None = None, default: str | bool | None = None):
    if default is None:
        default = ""
    state = request.args.get(name, default)
    if type == 'checkbox':
        state = str(state).lower() == 'true'
    store[name] = state
    if type == 'checkbox':
        return f'input {type=} {name=} {"checked" if state else ""}'
    elif type == 'radio':
        return f'input {type=} {name=} {value=} {"checked" if state == value else ""}'
    elif type == 'option':
        return f'option {type=} {value=} {"selected" if state == value else ""}'
    else:
        return f'input {type=} {name=} value="{esc(str(state))}"'

@serve.route()
def index() -> Iterator[Node | dict[str, str] | str]:
    global request_count
    request_count += 1

    server_age = round((datetime.now() - server_start).total_seconds(), 1)

    a = store.bool()
    b = store.int(default=1)
    c = store.str(default='c')

    with store.query:
        d = store.bool()
        e = store.int(default=1)

        vars = [a, b, c, d, e]

        store.assign_names(locals())
        for i in range(e.value):
            with store.sub(f'x{i}'):
                f = store.str(default='c', options='c c2 c3'.split())
                g = store.bool()
                h = store.int(default=1)
                store.assign_names(locals())
                vars += [f, g, h]

    with store.server:
        i = store.str(default='c')

    vars += [i]

    store.assign_names(locals())


    yield {
        'sheet': '''
            div > * {
                width: 100px;
                display: inline-block;
            }
        '''
    }
    yield from [
        div(div(v.full_name), div(v.provenance), div(str(v.value)), v.input())
        for v in vars
    ]
    yield V.button('defaults', onclick=store.defaults.goto())
    yield div(str(server_age))

def main():
    print('main', __name__)
    serve.run()

if __name__ == '__main__':
    main()
