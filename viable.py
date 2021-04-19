from flask import Flask, request
from textwrap import dedent
import time
app = Flask(__name__)

__table = str.maketrans({
    "<": "&lt;",
    ">": "&gt;",
    "&": "&amp;",
    "'": "&apos;",
    '"': "&quot;",
})

def esc(txt):
    return txt.translate(__table)

from itsdangerous.url_safe import URLSafeSerializer
import secrets

__serializer = URLSafeSerializer(secrets.token_hex(32))

__exposed = dict()

def expose(f, *args, **kws):
    name = f.__name__
    is_lambda = name == '<lambda>'
    if is_lambda:
        # note: memory leak
        name += str(len(__exposed))
    if name in __exposed:
        assert __exposed[name] == f
    __exposed[name] = f
    def inner(*args, **kws):
        msg = __serializer.dumps((name, *args, kws))
        return repr(f'/call/{msg}')
    if args or kws or name.startswith('<lambda>'):
        return inner(*args, **kws)
    else:
        return inner

def serve(f):

    @app.route('/call/<msg>', methods=['POST'])
    def call(msg):
        try:
            name, *args, kws = __serializer.loads(msg)
            more_args = request.json["args"]
            ret = __exposed[name](*args, *more_args, **kws)
            if ret is None:
                return '', 204
            else:
                return ret
        except:
            import traceback as tb
            tb.print_exc()
            return '', 400

    @app.route('/hot.js')
    def hot_js():
        return '''
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
                        prev.hasAttribute('replace') ||
                        next.hasAttribute('replace')
                    ) {
                        prev.replaceWith(next)
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
                        morph(document.body, doc.body)
                        for (let script of document.querySelectorAll('script[eval]')) {
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
            function set_query(q) {
                if (typeof q === 'string' && q[0] == '#') {
                    q = document.querySelector(q)
                }
                if (q instanceof HTMLFormElement) {
                    q = new FormData(q)
                } else if (q && typeof q === 'object') {
                    const kvs = Object.entries(q)
                    q = new FormData()
                    for (let [k, v] of kvs) {
                        q.append(k, v)
                    }
                }
                if (q instanceof FormData) {
                    q = '?' + new URLSearchParams(q).toString()
                }
                if (typeof q[0] === 'string' && q[0] == '?') {
                    next = location.href
                    if (next.indexOf('?') == -1 || !location.search) {
                        next = next.replace(/\?$/, '') + q
                    } else {
                        next = next.replace(location.search, q)
                    }
                    history.pushState(null, null, next)
                } else {
                    console.warn('Not a valid query', q)
                }
            }
        '''

    @app.route('/traceback.css')
    def traceback():
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
        ''', 200, {'Content-Type': 'text/css'}

    @app.route('/ping')
    def ping():
        time.sleep(115)
        return f'pong\n'

    @app.route('/')
    @app.route('/<path:path>')
    def index(path=None):
        try:
            if isinstance(f, str):
                body = f
                title = ''
            else:
                if path is None:
                    body = f()
                else:
                    body = f(path)
                title = f.__name__
        except Exception as e:
            import traceback as tb
            body = f'<pre>{esc(tb.format_exc())}</pre>'
            body += '<link href=/traceback.css rel=stylesheet>'
            title = 'error'
        return dedent('''
            <!DOCTYPE html>
            <html lang="en">
            <head>
            <!-- favicon because of chromium bug, see https://stackoverflow.com/a/36104057 -->
            <link rel="icon" type="image/png" href="data:image/png;base64,iVBORw0KGgo=">
            <meta charset="utf-8" />
            <title>{title}</title>
            <script defer src="/hmr.js"></script>
            </head>
            <body>
            {body}
            </body>
            </html>
        ''').strip().format(title=title, body=body)

    app.run()
