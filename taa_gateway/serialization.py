"""Canonical finite JSON; no credentials or executable objects in wire values."""
import hashlib
import json
import math


def _check(value):
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float and math.isfinite(value):
        return
    if type(value) is list:
        for item in value:
            _check(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _check(item)
        return
    raise ValueError("value is not finite, string-keyed JSON")


def canonical(value):
    _check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def copy_json(value):
    return json.loads(canonical(value))


def parse_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(text, object_pairs_hook=pairs)
    _check(value)
    return value
