init_globals = dict(globals())

from pprint import pprint as pp

import inotify_simple as inotify

from threading import Thread

# import aiohttp
# from aiohttp import web

import sys
import textwrap
from pathlib import Path
import traceback as tb

import time

class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


def clear():
    print("\033c\033[3J", end='')


def clear_imports(root_path):
    for name, module in list(sys.modules.items()):
        try:
            module_file = module.__file__
        except AttributeError:
            continue
        if module_file is None:
            continue
        path = Path(module_file).expanduser().resolve()
        try:
            rel = path.relative_to(root_path)
            if 'site-packages' not in rel.parts:
                # print('deleting module', name, rel, file=sys.stderr)
                # another idea is to use importlib.reload instead
                # this could be done on the main file as well...
                del sys.modules[name]
        except ValueError:
            pass


def clear_caches(path):
    '''
    Clear caches for end-user libraries. Currently only support snoop.
    '''
    path = Path(path)
    try:
        if path.suffix == '.py':
            import snoop
            snoop.formatting.Source.for_filename(path, {}, use_cache=False)
    except ModuleNotFoundError:
        pass


def serve(livepath, live_globals, flags):

    state = dotdict(
        running = False,
        interrupt = False,
        task = None,
        reloads = 0,
    )

    watcher = inotify.INotify()

    def run():
        if '' not in sys.path:
            sys.path = [''] + sys.path

        state.running = True
        try:
            # todo: change to importlib.import_module
            # then this globals-fiddling won't be needed
            # the module's globals can be accessed using e.g sys.modules
            filestr = open(livepath, 'r').read()
            co = compile(filestr, livepath, 'exec')
            state.reloads += 1
        except Exception:
            tb.print_exc()
            state.running = False
            return
        if flags['clear']:
            clear()
        if flags.debug:
            print(f'{time.strftime("%X")} running {livepath}')
        try:
            exec(co, live_globals)
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
        needs_clear_imports = False
        for event in events:
            path = Path(event.name)
            clear_caches(event.name)
            if path.suffix == '.py' and not path.samefile(livepath):
                needs_clear_imports = True
        if needs_clear_imports:
            clear_imports(livepath.expanduser().resolve().parent)
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
        raise ValueError('One live file required')
    livepath = Path(filepaths[0])
    flags = dotdict(
        clear = '-c' in flags or '--clear' in flags,
        debug = '-d' in flags or '--debug' in flags,
    )
    live_globals = dict(init_globals)
    serve(livepath, live_globals, flags)
