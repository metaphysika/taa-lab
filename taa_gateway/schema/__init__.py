"""Published Draft 2020-12 contracts; validators never fetch remote schemas."""
import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

from taa_gateway.serialization import canonical


@lru_cache(maxsize=None)
def _validator(name):
    source = json.loads((Path(__file__).parent / "objects.json").read_text())
    if name not in source["$defs"]:
        raise ValueError("unknown schema: " + name)
    schema = dict(source, **{"$ref": "#/$defs/" + name})
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate(name, value):
    canonical(value)
    _validator(name).validate(value)
