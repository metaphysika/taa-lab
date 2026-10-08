"""Load private credentials only when the owner runs a harness command."""
import os
from pathlib import Path


def load_keys(path):
    if not Path(path).exists():
        return
    with Path(path).open() as source:
        for line in source:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                if value:
                    os.environ.setdefault(name.strip(), value)
