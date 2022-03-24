import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from types import ModuleType
from typing import Sequence, Any

level = 0

def AddTrackingToSpec(spec: ModuleSpec):
    if spec.loader:
        spec_loader = spec.loader
    else:
        return None

    class TrackingLoader(Loader):
        def exec_module(self, module: ModuleType) -> None:
            if '(built-in)' in repr(module) or 'python3.' in repr(module):
                return spec_loader.exec_module(module)
            global level
            level += 1
            print('  ' * level + 'start', module)
            try:
                out = spec_loader.exec_module(module)
            finally:
                print('  ' * level + 'end  ', module)
                level -= 1
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

from types import ModuleType
from collections import UserDict

class TrackingDict(UserDict[str, ModuleType]):
    def __getitem__(self, k: str):
        print('  ' * level + '  get', k)
        return self.data[k]

def install():
    # sys.meta_path.insert(0, TrackingMetaPathFinder())
    sys.modules = TrackingDict(sys.modules)
