from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Sequence, Any, TypeAlias, Literal, Callable
from collections import UserDict
from dataclasses import dataclass, field
from threading import RLock
import sys
from contextlib import contextmanager
from pprint import pp

ordset: TypeAlias = dict[str, Literal[True]]

@dataclass(frozen=True)
class StackedModule:
    name: str
    deps: ordset = field(default_factory=dict)

main = sys.modules['__main__']
if main.__spec__:
    main_name = main.__spec__.name
else:
    main_name = '__main__'
sys.modules[main_name] = main

stack: list[StackedModule] = [StackedModule(main_name)]

@dataclass(frozen=True)
class TrackedModule:
    module: ModuleType
    deps: list[str]

    @property
    def name(self):
        return self.module.__name__

lock: RLock = RLock()
tracked: dict[str, TrackedModule] = {}

from inotify_simple import INotify, flags
from threading import Thread
from queue import Queue, Empty
import importlib

is_watching = False

def watch():
    global is_watching

    if is_watching:
        return
    else:
        is_watching = True

    inotify = INotify()

    rev: dict[int, str] = {} # watch descriptor to module name

    reinstalls = 0

    def reinstall():
        nonlocal reinstalls
        with lock:
            for k, v in tracked.items():
                mask = flags.MODIFY | flags.CLOSE_WRITE
                wd = inotify.add_watch(v.module.__file__, mask)
                rev[wd] = k
            pp(tracked)
            reinstalls += 1
            print('reinstalls:', reinstalls)
            print('watching:', rev)

    q = Queue[str]()

    def read():
        while True:
            for event in inotify.read():
                print(rev[event.wd], '::', *[str(m) for m in flags.from_mask(event.mask)])
                q.put_nowait(rev[event.wd])

    def reloader():
        needs_reload: set[str] = set()
        while True:
            print('reloader: reinstall')
            reinstall()
            print('reloader: waiting')
            needs_reload = {q.get()}
            with lock:
                try:
                    while True:
                        needs_reload.add(q.get(timeout=0.001))
                except Empty:
                    pass
                from collections import defaultdict
                rdeps = defaultdict[str, list[str]](list)
                for k, t in tracked.items():
                    for d in t.deps:
                        rdeps[d].append(k)
                pp(rdeps)
                def dfs(s: str, v: set[str]):
                    if s in v:
                        return
                    else:
                        v.add(s)
                    needs_reload.add(s)
                    for k in rdeps[s]:
                        dfs(k, v)
                print(f'{needs_reload = }')
                for s in list(needs_reload):
                    dfs(s, set())
                print(f'{needs_reload = }')
                roots = [
                    name
                    for name in needs_reload
                    if all(name not in t.deps for _, t in tracked.items())
                ]
                order: list[str] = []
                def inside_out(k: str, v: list[str]):
                    if k not in needs_reload:
                        return
                    t = tracked[k]
                    for d in t.deps:
                        inside_out(d, v)
                    if k in v:
                        return
                    else:
                        v += [k]
                for root in roots:
                    inside_out(root, order)
                print(f'{roots = }')
                print(f'{order = }')
                modules = [ tracked[name].module for name in order ]
            for m in modules:
                print('begin reimporting', m.__name__)
                importlib.reload(m)
                print('  end reimporting', m.__name__)

    Thread(target=read, daemon=False).start()
    Thread(target=reloader, daemon=False).start()

def boring(module: ModuleType):
    # if 'built-in' in repr(module):
    #     print(module.__spec__.name, module.__spec__.origin)
    if '(built-in)' in repr(module):
        return True
    if 'python3.' in repr(module):
        return True
    if 'viable/__init__.py' in repr(module):
        return True
    return False

@contextmanager
def track(name: str, origin: str):
    if stack[-1].name == name:
        yield
    elif not name:
        yield
    elif (module := sys.modules.get(name)) and boring(module):
        yield
    else:
        m = StackedModule(name)
        deps = m.deps
        print('  ' * len(stack) + 'begin', name, f'(origin: {origin})')
        with lock:
            stack.append(m)
        try:
            yield
        finally:
            with lock:
                if name in sys.modules:
                    module = sys.modules[name]
                    if not boring(module):
                        for s in stack:
                            s.deps[name] = True
                        for k, v in module.__dict__.items():
                            if isinstance(v, ModuleType) and not boring(v):
                                print('  ' * len(stack) + 'read ', v.__name__, f'(as {k})')
                                deps[v.__name__] = True
                        if name in deps:
                            del deps[name]
                        t = TrackedModule(module, list(deps.keys()))
                        tracked[t.name] = t
                stack.pop()
            print('  ' * len(stack) + 'end  ', name)

def AddTrackingToSpec(spec: ModuleSpec):
    if spec.loader:
        spec_loader = spec.loader
    else:
        return None

    class TrackingLoader(Loader):
        def exec_module(self, module: ModuleType) -> None:
            if boring(module):
                return spec_loader.exec_module(module)
            name = module.__name__
            with track(name, 'exec_module'):
                return spec_loader.exec_module(module)

        def create_module(self, spec: ModuleSpec):
            return spec_loader.create_module(spec)

        def load_module(self, fullname: str):
            return spec_loader.load_module(fullname)

        def module_repr(self, module: ModuleType):
            return spec_loader.module_repr(module)

    spec.loader = TrackingLoader()
    return spec

class TrackingMetaPathFinder(MetaPathFinder):
    def find_spec(self, fullname: str, path: Sequence[Any] | None, target: ModuleType | None = None) -> ModuleSpec | None:
        # print('find', fullname, path, target)
        meta_path = sys.meta_path and []
        for i, m in enumerate(sys.meta_path):
            if isinstance(m, TrackingMetaPathFinder):
                meta_path = sys.meta_path[i+1:]
                break
        for m in meta_path:
            spec = m.find_spec(fullname, path, target)
            if spec:
                spec = AddTrackingToSpec(spec)
            if spec:
                return spec
        return None

class TrackingDict(UserDict[str, ModuleType]):
    def __getitem__(self, k: str):
        module = self.data[k]
        if not boring(module):
            with lock:
                # print('  ' * len(stack) + 'query', k)
                for s in stack:
                    if k != s.name:
                        s.deps[k] = True
                main = TrackedModule(self.data[main_name], list(stack[0].deps.keys()))
                tracked[main_name] = main
        return self.data[k]

def track_import(f: Callable[..., Any]):
    def inner(*args: Any, **kws: Any):
        name = args[0]
        with track(name, '__import__'):
            return f(*args, **kws)
    return inner

def install():
    sys.meta_path.insert(0, TrackingMetaPathFinder())
    sys.modules = TrackingDict(sys.modules)
    if 0:
        # meta_path seems to be enough, but this might be needed in some case (?):
        import builtins
        builtins.__import__ = track_import(builtins.__import__)
