from importlib.abc import PathEntryFinder, Loader, MetaPathFinder
from importlib.machinery import ModuleSpec

import importlib
import builtins

import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Sequence, Any, Callable

from .import_hooks import AddTrackingToSpec

def TrackingPathEntryFinder(name: str) -> PathEntryFinder:
    print('TrackingPathEntryFinder', name)
    hooks = sys.path_hooks and []
    for i, f in enumerate(sys.path_hooks):
        if f == TrackingPathEntryFinder:
            hooks = sys.path_hooks[i+1:]
    for h in hooks:
        try:
            res = h(name)

            class X(PathEntryFinder):
                def find_spec(self, fullname: str, target: ModuleType | None=None):
                    spec = res.find_spec(fullname, target=target)
                    if spec:
                        return AddTrackingToSpec(spec)
                    else:
                        return None

            return X()
        except ImportError:
            continue
    raise ImportError

def repr_modules(*names: str):
    out: list[str] = []
    for name in names:
        if '_' in name:
            continue
        if m := sys.modules.get(name):
            # if '(built-in)' in repr(m):
            #     continue
            # if 'python3.' in repr(m):
            #     continue
            out += [name]
    return out

stack: list[set[str]] = []

def track_import(f: Callable[..., Any]):
    def inner(*args: Any, **kws: Any):
        global level
        name = args[0]
        refs: set[str] = set()
        for s in stack:
            s.add(name)
        stack.append(refs)
        res = f(*args, **kws)
        if name in refs:
            refs.remove(name)
        try:
            [me] = repr_modules(name)
            print(me, repr_modules(*refs))
        except:
            pass
        stack.pop()
        return res
    return inner

def install():
    builtins.__import__ = track_import(builtins.__import__)
    importlib.__import__ = track_import(importlib.__import__)
    sys.path_hooks.insert(0, TrackingPathEntryFinder)

