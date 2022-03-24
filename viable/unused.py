from importlib.abc import PathEntryFinder, Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Sequence, Callable, Any

import sys

import importlib
import builtins

def copy(f: Callable[..., Any]):
    fname = f.__name__
    print(f.__module__)
    told: set[str] = set()
    def inner(*args: Any, **kws: Any):
        name = args[0]
        first = name not in told
        told.add(name)
        first and print(fname, 'begin', name)
        res = f(*args, **kws)
        first and print(fname, 'end  ', name)
        try:
            mt = sys.modules[name]
            first and print(mt)
        except:
            pass
        return res
    return inner

def install_import_hook():
    builtins.__import__ = copy(builtins.__import__)
    importlib.__import__ = copy(importlib.__import__)
    importlib.import_module = copy(importlib.import_module)

from .import_hooks import AddTrackingToSpec

def install_path_hook():
    def F(name: str) -> PathEntryFinder:
        print('F', name)
        hooks = sys.path_hooks and []
        for i, f in enumerate(sys.path_hooks):
            if f == F:
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

    sys.path_hooks.insert(0, F)

