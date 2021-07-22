from __future__ import annotations
from typing import *

from utils import show

from dataclasses import *

from flask import request
import time
import textwrap

from viable import head, serve, esc, make_classes, expose, app
import utils
from utils import catch

# suppress flask logging
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

from datetime import datetime, timedelta
server_start = datetime.now()

last_msg = ''
server_redraws = 0

@expose
def example_exposed(*args: str):
    print(args)
    global last_msg
    last_msg = ' '.join(args)

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

@serve
def index() -> Iterator[head | str]:
    global server_redraws
    server_redraws += 1

    server_age = round((datetime.now() - server_start).total_seconds())


    yield head(f'<title>viable example</title>')

    yield r'''
        <body
            oninput="update_query(input_values()); refresh()"
            css="
                & { }
                body {
                    max-width: 13cm;
                    font-size: 16px;
                }
                ul {
                    list-style-type: none;
                    padding: 0;
                    margin: 0;
                }
                table {
                    table-layout: fixed;
                }
            ">
    '''

    store: dict[str, str | bool] = {}

    yield f'''

        <label>
            <{input(store, type='checkbox', name='autoreload')}/>
            autoreload
        </label>

        <p>Select a maintenance drone:</p>

        <div><label><{input(store, type="radio", name="drone", value="huey")}/>Huey</label></div>
        <div><label><{input(store, type="radio", name="drone", value="dewey")}/>Dewey</label></div>
        <div><label><{input(store, type="radio", name="drone", value="louie")}/>Louie</label></div>

        <label for="pet-select">Choose a pet:</label>
        <select name="pets" id="pet-select">
            <{input(store, type="option", name="pets", value="")}>--Please choose an option--</option>
            <{input(store, type="option", name="pets", value="dog")}>Dog</option>
            <{input(store, type="option", name="pets", value="cat")}>Cat</option>
            <{input(store, type="option", name="pets", value="hamster")}>Hamster</option>
            <{input(store, type="option", name="pets", value="parrot")}>Parrot</option>
            <{input(store, type="option", name="pets", value="spider")}>Spider</option>
            <{input(store, type="option", name="pets", value="goldfish")}>Goldfish</option>
        </select>

        <div>
        <{input(store, type='text', name='message')}
            oninput="call({example_exposed(str(request.remote_addr))}, event.target.value).then(refresh)"
        />
        </div> ​
    '''

    if store['autoreload']:
        yield '''
            <script eval>
                window.requestAnimationFrame(() => {
                    if (window.rt) window.clearTimeout(window.rt)
                    window.rt = window.setTimeout(() => refresh(0, () => 0), 100)
                })
            </script>
        '''

    scope = {**locals(), **globals()}
    scope = {
        k: v
        for k, v in scope.items()
        if k in """
            store
            last_msg
            server_age
            server_redraws
        """.split()
    }
    yield f'''<pre style="user-select: text">{show(scope, use_color=False, width=40)}</pre>'''

