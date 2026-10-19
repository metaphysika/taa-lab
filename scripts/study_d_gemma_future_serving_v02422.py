"""Prospective science sampler guard only. No arm launcher or execution entry point.

The reviewed speed winner must still be integrated/approved before science runs.
Inherited science sampling, seed, histories, parser and scorer remain frozen.
"""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, HERE/file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def serving_class():
    guard = load('sampler_guard', 'sampler_guard.py')
    guard.configure()  # before loading the inherited runtime or importing vLLM
    legacy = load('legacy_science', 'runtime.py')

    class Serving(legacy.Serving):
        def __init__(self, h, base, folder, volume, ledger, deadline, adapter):
            guard.configure()  # includes every engine-core subprocess
            super().__init__(h, base, folder, volume, ledger, deadline, adapter)
            legacy.write(folder/'sampler-guard.json',
                         guard.check_log((folder/'vllm-engine.log').read_text()))
            # No generation can be queued until this constructor returns.

    return Serving


def child_env(parent):
    """Required environment for any future science serving child; not a launcher."""
    return load('sampler_guard', 'sampler_guard.py').child_env(parent)
