"""Fail-closed check that set H evidence has a private destination. Not wired to any run yet.

Set H must never reach a public branch before evaluation, review and Chris's release approval.
The held-out executor (not yet built; live H dispatch still stops with held_out_sealed) must
call verify_private_destination before writing any evidence, and publish publicly only a
salted commitment and status (experiment_a/commitment.py). Chris creates the private
repository himself; nothing here creates or configures one.
"""
import json
import re
import urllib.request

from live_demo.adapter import Stop


def verify_private_destination(repository, token, public_repository, opener=urllib.request.urlopen):
    if (not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository or '') or
            repository.lower() == (public_repository or '').lower()):
        raise Stop('held_out_private_destination_unverified')
    request = urllib.request.Request('https://api.github.com/repos/' + repository, headers={
        'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json'})
    try:
        with opener(request, timeout=30) as response:
            data = json.load(response)
        if data.get('private') is not True or data.get('visibility') != 'private' or data.get('full_name', '').lower() != repository.lower():
            raise ValueError('not private')
    except Exception:
        raise Stop('held_out_private_destination_unverified') from None
    return repository
