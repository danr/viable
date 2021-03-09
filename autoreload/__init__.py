
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


def clear_caches(path):
    '''
    Clear caches for end-user libraries. Currently only support snoop.
    '''
    path = pathlib.Path(path)
    for name, module in sys.modules.items():
        try:
            module_file = module.__file__
        except AttributeError:
            continue
        if module_file is None:
            continue
        if path.samefile(module_file or ''):
            del sys.modules[name]
            break
    try:
        if path.suffix == '.py':
            import snoop
            snoop.formatting.Source.for_filename(path, {}, use_cache=False)
    except ModuleNotFoundError:
        pass


def serve(filepath, globals, flags):

    state = dotdict(
        running = False,
        interrupt = False,
        task = None,
        reloads = 0,
    )

    watcher = inotify.INotify()

    def run(updated_path=filepath):

        if '' not in sys.path:
            sys.path = [''] + sys.path

        state.running = True
        try:
            filestr = open(filepath, 'r').read()
            co = compile(filestr, filepath, 'exec')
            state.reloads += 1
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
        events = watcher.read()
        if flags.debug:
            print(events)
        for event in events:
            clear_caches(event.name)
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
