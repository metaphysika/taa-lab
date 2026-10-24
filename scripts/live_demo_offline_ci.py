#!/usr/bin/env python3
"""Run inside a fresh Linux network namespace after dependency installation."""
from pathlib import Path
import argparse
import socket
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser();p.add_argument('--require-network-blocked',action='store_true')
    args=p.parse_args()
    if args.require_network_blocked:
        try:
            with socket.create_connection(('1.1.1.1',443),timeout=1):pass
        except OSError:
            pass
        else:
            raise SystemExit('outbound network reachable: CI must fail closed')
    from unittest.mock import patch
    def blocked(*args,**kwargs):raise AssertionError('offline test attempted outbound connection')
    with patch.object(socket.socket,'connect',blocked),patch.object(socket.socket,'connect_ex',blocked):
        result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(
            ['tests.test_live_demo', 'tests.test_live_demo_review']))
    raise SystemExit(0 if result.wasSuccessful() else 1)


if __name__=='__main__':main()
