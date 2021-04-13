from __future__ import annotations
from dataclasses import *
from typing import *

import json
from datetime import datetime

import brc
from brc import b64png, pr

js, py = brc.client()

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

js.raw_eval('console.log("Reload: " + now)', now=now)

js('body').html = '''
  <h1>Major</h1>
  <div id=major></div>
  <h2>Minor</h1>
  <img id=plot />
  <div id=minor></div>
  <div id=counter></div>
  <div id=footer></div>
'''


def skip():
    import seaborn as sns
    p=sns.scatterplot(x=[0, 2, 3, 4], y=[1, 2, 3, 2])
    # pp(repr(p.figure), dir(p.figure))
    # pp(p.figure.savefig)
    import io
    buf = io.BytesIO()
    p.figure.savefig(buf, format='png')
    import base64
    js('#plot').src = b64png(buf)

js('#major').style = 'color:#99c; font-family: monospace; font-size: 5em;'
js('#major').outerHTML = '<input id=txt type=text />'
js('#txt').oninput = py.handler(lambda target_value: [
    js('#minor').__setattr__('html', pr(target_value)),
    js('#footer').outerHTML.__iadd__(f'<pre>{pr(target_value)}</pre>'),
])

js('#minor').html = 'lol #' + now
js('#minor').style = 'color:#9c9; font-family: monospace; font-size: 5em;'
js('#minor').onclick = py.handler(lambda x, y: pr((x, y)))

js('#minor').html += ' also this!'
js('#minor').html += ' and this!'
js('#minor').style += 'transform: rotate(-3deg);'

x = 0
while True:
    x += 1
    if x % 1e6 == 0:
        print(x)
        js('#counter').html = f'<pre>x: {x}</pre>'

