from __future__ import annotations
from typing import *

from dataclasses import dataclass
import os
import pickle
import re
import secrets
import sys
import textwrap
import time

from flask import Flask, request
from itsdangerous.url_safe import URLSafeSerializer # type: ignore

__serializer = URLSafeSerializer(secrets.token_hex(32), serializer=pickle) # type: ignore

@dataclass(frozen=True)
class head:
    content: str

def make_classes(html: str) -> tuple[head, str]:
    classes: dict[str, str] = {}
    def repl(m: re.Match[str]) -> str:
        decls = textwrap.dedent(m.group(1)).strip()
        if decls in classes:
            name = classes[decls]
        else:
            name = f'css-{len(classes)}'
            classes[decls] = name
        return name

    html_out = re.sub('css="([^"]*)"', repl, html, flags=re.MULTILINE)
    style = '\n'.join(
        decls.replace('&', f'[{name}]')
        if '&' in decls else
        f'[{name}] {{ {decls} }}'
        for decls, name in classes.items()
    )
    return head(f'<style>{style}</style>'), html_out


def esc(txt: str, __table: dict[int, str] = str.maketrans({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    '"': "&quot;",
})) -> str:
    return txt.translate(__table)

__exposed: dict[str, Callable[..., Any]] = dict()

def expose(f: Callable[..., Any], *args: Any, **kws: Any) -> Callable[..., Any]:
    name = f.__name__
    is_lambda = name == '<lambda>'
    if is_lambda:
        # note: memory leak
        name += str(len(__exposed))
    if name in __exposed:
        assert __exposed[name] == f                  # type: ignore
    __exposed[name] = f                              #
    def inner(*args, **kws):                         # type: ignore
        msg: bytes = __serializer.dumps((name, *args, kws)) # type: ignore
        return f"'/call/{msg.decode()}'"                      #
    if args or kws or name.startswith('<lambda>'):   #
        return inner(*args, **kws)                   # type: ignore
    else:                                            #
        inner.call = lambda *a, **ka: f(*a, **ka)    # type: ignore
        return inner                                 # type: ignore

app = Flask(__name__)

def serve(f: Callable[..., str | Iterable[head | str]]):

    @app.route('/call/<msg>', methods=['POST'])
    def call(msg: str):
        try:
            name, *args, kws = __serializer.loads(msg)      # type: ignore
            more_args = request.json["args"]                # type: ignore
            ret = __exposed[name](*args, *more_args, **kws) # type: ignore
            if ret is None:
                return '', 204
            else:
                return ret
        except:
            import traceback as tb
            tb.print_exc()
            return '', 400

    @app.route('/hot.js')
    def hot_js_route():
        return hot_js, {'Content-Type': 'application/javascript'}

    @app.route('/traceback.css')
    def traceback_css():
        return '''
            body {
                margin: 0 auto;
                padding: 5px;
                max-width: 800px;
                background: #222;
                color: #f2777a;
                font-size: 16px;
            }
            pre {
                white-space: pre-wrap;
                overflow-wrap: break-word;
            }
        ''', {'Content-Type': 'text/css'}

    @app.route('/ping')
    def ping():
        time.sleep(115)
        return 'pong\n', {'Content-Type': 'text/plain'}

    @app.route('/')
    @app.route('/<path:path>')
    def index(path: str|None=None):
        parts = []
        try:
            if isinstance(f, str):
                parts = f
                title = ''
            else:
                if path is None:
                    parts = f()
                else:
                    parts = f(path)
                title = f.__name__
        except Exception as e:
            import traceback as tb
            title = 'error'
            parts = [
               head('<link href=/traceback.css rel=stylesheet>'),
               head('<title>error</title>'),
               f'<pre>{esc(tb.format_exc())}</pre>'
            ]
        if isinstance(parts, str):
            parts = [parts]

        parts = list(parts)
        heads = ['''
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
        ''']
        heads += [part.content for part in parts if isinstance(part, head)]
        bodies = [part for part in parts if isinstance(part, str)]
        if not any(hd.lstrip().startswith('<title') for hd in heads):
            heads += [f'<title>{title}</title>']
        if not any(hd.lstrip().startswith('<link rel="icon"') for hd in heads):
            # <!-- favicon because of chromium bug, see https://stackoverflow.com/a/36104057 -->
            heads += ['<link rel="icon" type="image/png" href="data:image/png;base64,iVBORw0KGgo=">']
        if bodies and not bodies[0].lstrip().startswith('<body'):
            bodies = ['<body>', *bodies, '</body>']
        css_head, body = make_classes('\n'.join(bodies))
        head_str = '\n'.join([*heads, css_head.content])
        html = textwrap.dedent('''
            <!doctype html>
            <html lang="en">
            <head>
            <meta charset="utf-8" />
            <script defer src="/hot.js"></script>
            {head}
            </head>
            {body}
            </html>
        ''').strip().format(head=head_str, body=body)
        return html

    try:
        from flask_compress import Compress # type: ignore
        Compress(app)
    except Exception as e:
        print('Not using flask_compress:', str(e), file=sys.stderr)

    if sys.argv[0].endswith('.py'):
        host = os.environ.get('VIABLE_HOST')
        port = os.environ.get('VIABLE_PORT')
        port = int(port) if port else None
        app.run(host=host, port=port)

hot_js = r'''
    function call(url, ...args) {
        return fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ args: args }),
        })
    }
    function morph(prev, next) {
        if (
            prev.nodeType === Node.ELEMENT_NODE &&
            next.nodeType === Node.ELEMENT_NODE &&
            prev.tagName === next.tagName
        ) {
            if (
                (prev.hasAttribute('id') || next.hasAttribute('id')) &&
                prev.getAttribute('id') !== next.getAttribute('id')
            ) {
                prev.replaceWith(next)
            }
            if (next.hasAttribute('replace')) {
                prev.replaceWith(next)
                return
            }
            if (
                next.hasAttribute('protect')
                // && prev.id === next.id ?
            ) {
                return
            }
            for (let name of prev.getAttributeNames()) {
                if (!next.hasAttribute(name)) {
                    prev.removeAttribute(name)
                }
            }
            for (let name of next.getAttributeNames()) {
                if (
                    !prev.hasAttribute(name) ||
                    next.getAttribute(name) !== prev.getAttribute(name)
                ) {
                    prev.setAttribute(name, next.getAttribute(name))
                }
            }
            if (prev.tagName === 'INPUT' && document.activeElement !== prev) {
                prev.value = next.getAttribute('value')
                prev.checked = next.hasAttribute('checked')
            }
            const pc = [...prev.childNodes]
            const nc = [...next.childNodes]
            const num_max = Math.max(pc.length, nc.length)
            for (let i = 0; i < num_max; ++i) {
                if (i >= nc.length) {
                    prev.removeChild(pc[i])
                } else if (i >= pc.length) {
                    prev.appendChild(nc[i])
                } else {
                    morph(pc[i], nc[i])
                }
            }
        } else if (
            prev.nodeType === Node.TEXT_NODE &&
            next.nodeType === Node.TEXT_NODE
        ) {
            if (prev.textContent !== next.textContent) {
                prev.textContent = next.textContent
            }
        } else {
            prev.replaceWith(next)
        }
    }
    let in_progress = false
    let rejected = false
    async function refresh(i=0, and_then) {
        if (!and_then) {
            if (in_progress) {
                rejected = true
                return
            }
            in_progress = true
        }
        let text = null
        try {
            const resp = await fetch(window.location.href)
            text = await resp.text()
        } catch (e) {
            if (i > 0) {
                window.setTimeout(() => refresh(i-1, and_then), i < 300 ? 1000 : 16)
            } else {
                console.warn('timeout', e)
            }
        }
        if (text !== null) {
            try {
                const parser = new DOMParser()
                const doc = parser.parseFromString(text, "text/html")
                morph(document.head, doc.head)
                morph(document.body, doc.body)
                for (const script of document.querySelectorAll('script[eval]')) {
                    const global_eval = eval
                    global_eval(script.textContent)
                }
            } catch(e) {
                console.warn(e)
            }
            if (and_then) {
                and_then()
            } else if (in_progress) {
                in_progress = false
                if (rejected) {
                    rejected = false
                    refresh()
                }
            }
        }
    }
    async function long_poll() {
        try {
            while (await fetch('/ping'));
        } catch (e) {
            refresh(600, long_poll)
        }
    }
    long_poll()
    window.onpopstate = () => refresh()
    function input_values() {
        const inputs = document.querySelectorAll('input:not([type=radio]),input[type=radio]:checked,select')
        const vals = {}
        for (let i of inputs) {
            if (!i.name) {
                console.error(i, 'has no name attribute')
                continue
            }
            if (i.type == 'radio') {
                console.assert(i.checked)
                vals[i.name] = i.value
            } else if (i.type == 'checkbox') {
                vals[i.name] = i.checked
            } else {
                vals[i.name] = i.value
            }
        }
        return vals
    }
    function get_query(q) {
        return Object.fromEntries(new URLSearchParams(location.search))
    }
    function update_query(kvs) {
        return set_query({...get_query(), ...kvs})
    }
    function set_query(kvs) {
        q = '?' + new URLSearchParams(kvs).toString()
        next = location.href
        if (next.indexOf('?') == -1 || !location.search) {
            next = next.replace(/\?$/, '') + q
        } else {
            next = next.replace(location.search, q)
        }
        history.replaceState(null, null, next)
    }
'''

hot_js = re.sub(' {2,}', '', hot_js.strip())
