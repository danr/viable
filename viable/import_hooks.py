from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Sequence, Any, TypeAlias, Literal, Callable
from collections import UserDict
from dataclasses import dataclass, field
from pprint import pprint
import builtins
import sys

ordset: TypeAlias = dict[str, Literal[True]]

@dataclass(frozen=True)
class StackedModule:
    name: str
    deps: ordset = field(default_factory=dict)

stack: list[StackedModule] = [StackedModule('__main__')]

@dataclass(frozen=True)
class TrackedModule:
    module: ModuleType
    deps: list[str]

    @property
    def name(self):
        return self.module.__name__

tracked: dict[str, TrackedModule] = {}

def boring(module: ModuleType):
    # if 'built-in' in repr(module):
    #     print(module.__spec__.name, module.__spec__.origin)
    return '(built-in)' in repr(module) or 'python3.' in repr(module)

from contextlib import contextmanager

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
        stack.append(m)
        try:
            yield
        finally:
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
            print('  ' * len(stack) + 'query', k)
            for s in stack:
                s.deps[k] = True
            main = TrackedModule(self.data['__main__'], list(stack[0].deps.keys()))
            tracked[main.name] = main
            # pprint(main)
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
    # meta_path seems to be enough, but this might be needed in some case (?):
    # builtins.__import__ = track_import(builtins.__import__)
