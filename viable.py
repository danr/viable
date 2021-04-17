from flask import Flask, request
from textwrap import dedent
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

def serve(f):
    @app.route('/hmr.js')
    def hmr():
        return '''
            async function refresh(i, and_then) {
                try {
                    const resp = await fetch(window.location.href)
                    const text = await resp.text()
                    const parser = new DOMParser();
                    const doc = parser.parseFromString(text, "text/html");
                    const focus_elem = document.activeElement
                    const focus_id = focus_elem?.id
                    const focus_range = focus_elem && [
                        focus_elem.selectionStart,
                        focus_elem.selectionEnd,
                        focus_elem.selectionDirection,
                    ]
                    document.body.replaceWith(doc.body)
                    const new_focus_elem = document.getElementById(focus_id)
                    if (new_focus_elem) {
                        try {
                            new_focus_elem.focus()
                            if (focus_range
                                    && new_focus_elem.setSelectionRange
                                    && new_focus_elem.type !== 'radio'
                                    && new_focus_elem.type !== 'range'
                                ) {
                                new_focus_elem.setSelectionRange(...focus_range)
                            }
                        } catch(e) {
                            console.warn(e)
                        }
                    }
                    and_then && and_then()
                } catch (e) {
                    if (i > 0) {
                        window.setTimeout(() => refresh(i-1, and_then), i < 300 ? 1000 : 16)
                    } else {
                        console.warn('timeout', e)
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
            function set_query(q) {
                if (typeof q === 'string' && q[0] == '#') {
                    q = document.querySelector(q)
                }
                console.log(q)
                if (q instanceof HTMLFormElement) {
                    q = new FormData(q)
                } else if (q && typeof q === 'object') {
                    const kvs = Object.entries(q)
                    q = new FormData()
                    for (let [k, v] of kvs) {
                        q.append(k, v)
                        console.log(q, k, v)
                    }
                    console.log(q)
                }
                console.log(q)
                if (q instanceof FormData) {
                    q = '?' + new URLSearchParams(q).toString()
                }
                console.log(q)
                if (typeof q[0] === 'string' && q[0] == '?') {
                    next = location.href
                    if (next.indexOf('?') == -1 || !location.search) {
                        next = next.replace(/\?$/, '') + q
                    } else {
                        next = next.replace(location.search, q)
                    }
                    console.log(next)
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
        import time
        time.sleep(115)
        return f'pong\n'

    @app.route('/favicon.ico')
    def favicon():
        return ''

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
