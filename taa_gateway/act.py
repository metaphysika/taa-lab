"""Registered, trusted effect descriptions; arbitrary tools are rejected."""
from dataclasses import dataclass, replace

from jsonschema import Draft202012Validator

from taa_gateway.schema import validate
from taa_gateway.serialization import copy_json


@dataclass(frozen=True)
class Tool:
    name: str
    arguments_schema: dict
    describe: object
    reads: tuple = ()
    authorization_rule: object = "AU1"
    purposes: tuple = ()
    referral: object = None
    scope: object = None
    amount_argument: object = None


class ToolRegistry:
    def __init__(self, tools):
        self.__tools = {}
        for tool in tools:
            if (not isinstance(tool.name, str) or not tool.name or tool.name in self.__tools or
                    not callable(tool.describe) or (tool.scope is not None and not callable(tool.scope)) or
                    (tool.authorization_rule is not None and
                     (not isinstance(tool.authorization_rule, str) or not tool.authorization_rule))):
                raise ValueError("invalid or duplicate registered tool")
            if set(tool.reads) & {"grant", "purpose", "stored_order"}:
                raise ValueError("effect descriptions cannot condition on authority or orders")
            schema = copy_json(tool.arguments_schema)
            def local_only(value):
                if isinstance(value, dict):
                    if any(key in value and (not isinstance(value[key], str) or not value[key].startswith("#"))
                           for key in ("$ref", "$dynamicRef")):
                        raise ValueError("tool schemas must not fetch remote references")
                    for item in value.values():
                        local_only(item)
                elif isinstance(value, list):
                    for item in value:
                        local_only(item)
            local_only(schema)
            Draft202012Validator.check_schema(schema)
            if tool.authorization_rule is None and not tool.referral:
                raise ValueError("a registered tool without an authorization rule needs a referral")
            tool = replace(tool, arguments_schema=schema, reads=tuple(tool.reads),
                           purposes=tuple(tool.purposes), referral=copy_json(tool.referral))
            # Retain our own schema, not a caller-owned mutable dictionary.
            self.__tools[tool.name] = (tool, Draft202012Validator(copy_json(schema)))

    def get(self, name, arguments):
        if name not in self.__tools:
            raise ValueError("unregistered tool: " + str(name))
        tool, validator = self.__tools[name]
        validator.validate(arguments)
        return replace(tool, arguments_schema=copy_json(tool.arguments_schema), referral=copy_json(tool.referral))

    @staticmethod
    def describe(tool, arguments, view):
        act = tool.describe(copy_json(arguments), view)
        validate("act", act)
        if act["operation"] != tool.name:
            raise ValueError("effect description does not identify the registered operation")
        resources = (tool.scope(copy_json(arguments), view) if tool.scope else copy_json(arguments))
        if type(resources) is not dict:
            raise ValueError("trusted resource projection must be an object")
        return copy_json(act), copy_json(resources)
