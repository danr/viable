
init_globals = dict(globals())

from pprint import pprint as pp

import inotify_simple as inotify

from threading import Thread

# import aiohttp
# from aiohttp import web

import sys
import textwrap
import pathlib

import traceback as tb

import time

class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def clear():
    print("\033c\033[3J", end='')


def serve(filepath, globals, flags):

    state = dotdict(
        running = False,
        interrupt = False,
        task = None,
    )

    watcher = inotify.INotify()

    def run():
        state.running = True
        try:
            with open(filepath, 'r') as fp:
                filestr = fp.read()
            co = compile(filestr, filepath, 'exec')
        except Exception:
            tb.print_exc()
            state.running = False
            return
        # os.chdir(pathlib.Path(filepath).absolute())
        if flags['clear']:
            clear()
        if flags.debug:
            print(f'{time.strftime("%X")} running {filepath}')
        try:
            exec(co, globals)
        except KeyboardInterrupt as e:
            if state.interrupt:
                if flags.debug:
                    print(f'{time.strftime("%X")} interrupted')
            else:
                watcher.close()
                raise e
        except:
            tb.print_exc()
        state.running = False
        state.interrupt = False

    def listen():
        watcher.add_watch(path='.', mask=inotify.flags.CLOSE_WRITE | inotify.flags.ONESHOT)
        event = watcher.read()
        if flags.debug:
            print(event)
        if state.running:
            import _thread
            state.interrupt = True
            _thread.interrupt_main()

    while True:
        thread = Thread(target=listen, daemon=True)
        thread.start()
        run()
        thread.join()

def main():
    argv = sys.argv[1:]
    flags = { a for a in argv if a.startswith('-') }
    filepaths = [ a for a in argv if a not in flags ]
    if len(filepaths) != 1:
        raise ValueError('One filepath required')
    filepath = filepaths[0]
    flags = dotdict(
        clear = '-c' in flags or '--clear' in flags,
        debug = '-d' in flags or '--debug' in flags,
    )
    globals = dict(
        init_globals,
        store=dotdict(),
        flags=flags,
        dotdict=dotdict,
    )
    serve(filepath, globals, flags)
