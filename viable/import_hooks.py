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

from inotify_simple import INotify, flags, masks
from threading import Thread
from queue import Queue, Empty
import importlib
from collections import defaultdict

@dataclass
class Watcher:
    is_watching = False
    inotify: INotify = field(default_factory=INotify)
    module_wd: dict[int, str] = field(default_factory=dict) # watch descriptor to module name
    reinstalls: int = 0
    module_reload_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    q: Queue[str] = field(default_factory=Queue[str])

    def print(self, *xs: Any):
        if 0:
            print(*xs)

    def pp(self, x: Any):
        if 0:
            pp(x)

    def watch(self):
        if self.is_watching:
            return
        else:
            self.is_watching = True

        Thread(target=self.read, daemon=False).start()
        Thread(target=self.reloader, daemon=False).start()

    def reinstall(self):
        with lock:
            for k, v in tracked.items():
                mask = flags.CLOSE_WRITE | flags.MODIFY
                wd = self.inotify.add_watch(v.module.__file__, mask)
                self.module_wd[wd] = k
            self.pp({'tracked': tracked})
            self.print('reinstalls:', self.reinstalls)
            self.print('watching:', self.module_wd)
            self.reinstalls += 1

    def read(self):
        while True:
            for event in self.inotify.read():
                self.print(self.module_wd[event.wd], '::', *[str(m) for m in flags.from_mask(event.mask)])
                self.q.put_nowait(self.module_wd[event.wd])

    def reloader(self):
        while True:
            self.print('reloader: reinstall')
            self.reinstall()
            self.print('reloader: waiting...\n')
            needs_reload_list: list[str] = [self.q.get()]
            with lock:
                try:
                    while True:
                        needs_reload_list += [self.q.get(timeout=0.005)]
                except Empty:
                    pass
                self.print(f'{needs_reload_list = }')
                needs_reload: set[str] = set(needs_reload_list)
                rev_deps = defaultdict[str, list[str]](list)
                for k, t in tracked.items():
                    for d in t.deps:
                        rev_deps[d].append(k)
                self.pp({'rev_deps': rev_deps})
                def dfs(s: str, visited: set[str]) -> set[str]:
                    if s not in visited:
                        visited.add(s)
                        for k in rev_deps[s]:
                            dfs(k, visited)
                    return visited
                self.print(f'{needs_reload = }')
                for s in list(needs_reload):
                    needs_reload |= dfs(s, set())
                self.print(f'{needs_reload = }')
                roots = [
                    name
                    for name in needs_reload
                    if all(name not in t.deps for _, t in tracked.items())
                ]
                def inside_out(k: str, order: list[str]):
                    if k not in needs_reload:
                        return
                    t = tracked[k]
                    for d in t.deps:
                        inside_out(d, order)
                    if k in order:
                        return
                    else:
                        order += [k]
                order: list[str] = []
                for root in roots:
                    inside_out(root, order)
                self.print(f'{roots = }')
                self.print(f'{order = }')
                modules = [ tracked[name].module for name in order ]

            # rapidly saving .py files can cause the cached .pyc bytecode to get stale
            sys.dont_write_bytecode = True

            try:
                for m in modules:
                    # self.print('begin reimporting', m.__name__)
                    self.module_reload_counts[m.__name__] += 1
                    importlib.reload(m)
                    # self.print('  end reimporting', m.__name__)
                names = [m.__name__ for m in modules]
                print(f'[reloaded {", ".join(names)}]')
            except:
                import traceback
                traceback.print_exc()

    def module_reload_count(self, m: str):
        return self.module_reload_counts[m]

watcher = Watcher()
watch = watcher.watch

def boring(module: ModuleType):
    if '(built-in)' in repr(module):
        return True
    if 'python3.' in repr(module):
        return True
    if 'viable/__init__.py' in repr(module):
        return True
    return False

def track_debug(action: str, *xs: Any):
    if 0:
        print('  ' * len(stack) + action.rjust(5, ' '), *xs)

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
        track_debug('begin', name, f'(origin: {origin})')
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
                                track_debug('read', v.__name__, f'(as {k})')
                                deps[v.__name__] = True
                        if name in deps:
                            del deps[name]
                        t = TrackedModule(module, list(deps.keys()))
                        tracked[t.name] = t
                stack.pop()
            track_debug('end', name)

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
                track_debug('query', k)
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
