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

def install():
    sys.path_hooks.insert(0, TrackingPathEntryFinder)

