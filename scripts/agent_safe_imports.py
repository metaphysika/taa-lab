"""Block sealed imports before Python can open their source."""
import importlib.abc
import sys

class NoSealed(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'exploratory.ft1.sealed':
            raise RuntimeError('sealed import forbidden in agent-safe mode')

def install():
    if 'exploratory.ft1.sealed' in sys.modules:
        raise RuntimeError('sealed already imported')
    sys.meta_path.insert(0, NoSealed())

if __name__ == '__main__':
    import runpy
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    install()
    args = sys.argv[1:]
    if args[0] == '-m':
        sys.argv = args[1:]
        runpy.run_module(args[1], run_name='__main__', alter_sys=True)
    else:
        sys.argv = args
        runpy.run_path(args[0], run_name='__main__')
