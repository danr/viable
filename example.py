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

from flask import g, after_this_request
from flask.wrappers import Response
import sqlite3

with sqlite3.connect('example.db') as con:
    con.executescript('''
        pragma journal_mode=WAL;
        create table if not exists todos (
            id integer primary key autoincrement,
            text text default '' not null,
            done int default 0 not null,
            created datetime default (datetime('now', 'localtime')) not null,
            deleted datetime default null
        );
        insert into todos(text)
            select "add some todos"
            where (select count(*) from todos) == 0;
    ''')

def serve_reload(reason: str):
    @after_this_request
    def later(response: Response) -> Response:
        print('serve_reload', reason)
        serve.reload()
        return response

def get_con() -> sqlite3.Connection:
    if 'con' in g:
        return g.con
    else:
        con = sqlite3.connect('example.db')
        con.create_function('serve_reload', 1, serve_reload)
        con.executescript('''
            create temp trigger notify_update
                after update on todos
                begin
                    select serve_reload('update');
                end;
            create temp trigger notify_insert
                after insert on todos
                begin
                    select serve_reload('insert');
                end;
        ''')
        g.con = con
        @after_this_request
        def cleanup(response: Response) -> Response:
            con.commit()
            con.close()
            del g.con
            return response
        return con

@serve.expose
def sql(cmd: str, *args: Any) -> Any:
    con = get_con()
    con.execute(cmd, args)
    con.commit()

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

    with store.query:
        visibility = store.str(default='all', options='all done todo'.split())

    store.assign_names(locals())

    with sqlite3.connect('example.db') as con:
        con.row_factory = sqlite3.Row
        yield visibility.input()

        yield V.button('add todo', onclick=sql.call('insert into todos default values'))

        if con.execute('select exists (select 1 from todos where deleted is not null)').fetchone()[0]:
            yield V.button('undo delete', onclick=sql.call('''
                update todos set deleted = NULL
                    where rowid = (select rowid from todos order by deleted desc limit 1)
            '''))

        stmt = 'select id, text, done from todos where deleted is null'
        if visibility.value == 'done':
            stmt += ' and done'
        elif visibility.value == 'todo':
            stmt += ' and not done'
        for row in con.execute(stmt):
            id = row['id']
            print(dict(zip(row.keys(), row)))
            yield V.div(
                V.input(
                    type='checkbox',
                    checked=bool(row['done']),
                    oninput=sql.call('update todos set done = ? where rowid = ?', js('this.checked'), id),
                ),
                V.input(
                    value=row['text'],
                    oninput=sql.call('update todos set text = ? where rowid = ?', js('this.value'), id),
                ),
                V.button(
                    'delete',
                    onclick=sql.call('update todos set deleted = strftime("%Y-%m-%d %H:%M:%f", "now", "localtime") where rowid = ?', id),
                ),
            )

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
