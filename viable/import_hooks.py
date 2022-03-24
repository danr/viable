from importlib.abc import PathEntryFinder, Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Sequence, Any

from types import ModuleType
from typing import Callable, Any

import sys

import importlib
import builtins

from types import ModuleType
from collections import UserDict

stack: list[set[str]] = []

def AddTrackingToSpec(spec: ModuleSpec):
    if spec.loader:
        spec_loader = spec.loader
    else:
        return None

    class TrackingLoader(Loader):
        def exec_module(self, module: ModuleType) -> None:
            if '(built-in)' in repr(module) or 'python3.' in repr(module):
                return spec_loader.exec_module(module)
            name = module.__name__
            refs: set[str] = set()
            for s in stack:
                s.add(name)
            stack.append(refs)
            level = len(stack)
            print('  ' * level + 'start', module)
            try:
                out = spec_loader.exec_module(module)
            finally:
                if name in refs:
                    refs.remove(name)
                print('  ' * level + 'end  ', module, refs)
                stack.pop()
            return out

        def create_module(self, spec: ModuleSpec):
            return spec_loader.create_module(spec)

        def load_module(self, fullname: str):
            return spec_loader.load_module(fullname)

        def module_repr(self, module: ModuleType): return spec_loader.module_repr(module)

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
        for s in stack:
            s.add(k)
        return self.data[k]

def install():
    sys.meta_path.insert(0, TrackingMetaPathFinder())
    sys.modules = TrackingDict(sys.modules)
