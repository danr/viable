# python autoreload

goal:
- keep state in a python process while allowing reload, similar to jupyter (and a repl)
- integrate jedi in the running process for kakoune
- control a browser and allow communication back and forth and hot reload
- serve many users to a browser non-reloading

available globals:
- `dotdict`: a dictionary which forwards getattr to get
- `store`: a dotdict which is persisted between reloads, unique for each user
- `shared`: a dotdict shared between all connected users is serve mode
- `doc`: API to the browser, TBD

modes:
- repl mode
    * only one copy of `store` exists,
    * each connecting websocket gets sent the same thing (!!)
    * file is reloaded when saving
    * ad-hoc code can be executed in the process (such as jedi)
- dev mode
    * each connecting user gets an own `store`
    * file is reloaded when saving
    * ad-hoc code not available
- serve mode
    * each connecting user gets an own `store`
    * file is not reloaded
    * ad-hoc code not available

```python
with doc.body:
    div.rows(
        'boo boo',
        onclick=lambda x: bla bla
    )

# replaces or adds
doc.body = div.cols('a','b','c')
doc.body += div.cols('a','b','c')

# replaces
with doc('body'):

# appends
with doc('body').append:

doc.sheets = ['./bootstrap.css']
doc.scripts = ['./jquery.js']

doc.body = html('''
    <form>
    </form>
''')

doc.eval('plot.activate(data)', data=[[...]])
```
