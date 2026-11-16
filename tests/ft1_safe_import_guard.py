"""Fresh-process import guard for the entire agent-safe fast set."""
import importlib
import sys
from scripts.run_fast_checks import FAST
for name in FAST:
    importlib.import_module(name)
assert 'exploratory.ft1.sealed' not in sys.modules
