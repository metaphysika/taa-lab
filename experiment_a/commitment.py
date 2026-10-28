"""Salted commitment for private amendment packages (e.g. set H target predicates).

A custodian who already holds the private files runs this on their own machine:

    python3 -m experiment_a.commitment commit FILE [FILE ...] --salt-out PRIVATE/salt.txt

It prints one digest to publish before the run. The salt is random (32 bytes), so a small,
guessable package cannot be recovered from the digest. The salt file stays private with the
package until release; then anyone can check:

    python3 -m experiment_a.commitment verify DIGEST --salt-file salt.txt FILE [FILE ...]

The digest covers each file's name and SHA-256 in sorted order, so renaming, adding, removing
or editing any file changes it. Nothing here reads keys or touches the network.
"""
import argparse
import hashlib
import hmac
import secrets
import sys
from pathlib import Path

DOMAIN = b'taa-lab/experiment-a/commitment/v1\n'


def manifest(paths):
    lines = []
    for path in sorted(Path(p) for p in paths):
        lines.append(path.name + ' ' + hashlib.sha256(path.read_bytes()).hexdigest())
    names = [line.split(' ')[0] for line in lines]
    if len(set(names)) != len(names):
        raise ValueError('duplicate file names in package')
    return ('\n'.join(lines) + '\n').encode()


def digest(paths, salt_hex):
    salt = bytes.fromhex(salt_hex)
    if len(salt) != 32:
        raise ValueError('salt must be 32 bytes of hex')
    return hashlib.sha256(DOMAIN + salt + manifest(paths)).hexdigest()


def commit(paths, salt_out):
    salt_out = Path(salt_out)
    if salt_out.exists():
        raise FileExistsError('refusing to overwrite an existing salt file')
    salt_hex = secrets.token_hex(32)
    salt_out.write_text(salt_hex + '\n')
    return digest(paths, salt_hex)


def verify(expected, salt_hex, paths):
    return hmac.compare_digest(expected, digest(paths, salt_hex))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('commit'); c.add_argument('files', nargs='+'); c.add_argument('--salt-out', required=True)
    v = sub.add_parser('verify'); v.add_argument('digest'); v.add_argument('files', nargs='+')
    v.add_argument('--salt-file', required=True)
    args = parser.parse_args(argv)
    if args.command == 'commit':
        print(commit(args.files, args.salt_out))
        return 0
    ok = verify(args.digest, Path(args.salt_file).read_text().strip(), args.files)
    print('match' if ok else 'MISMATCH')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
