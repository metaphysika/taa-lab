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
    stage: object = None
    scope_absent_is_violation: tuple = ()
    scope_dimensions: object = None
    scope_references: object = None


class ToolRegistry:
    def __init__(self, tools):
        self.__tools = {}
        for tool in tools:
            if (not isinstance(tool.name, str) or not tool.name or tool.name in self.__tools or
                    not callable(tool.describe) or (tool.scope is not None and not callable(tool.scope)) or
                    (tool.stage is not None and not callable(tool.stage)) or
                    (tool.scope_references is not None and not callable(tool.scope_references)) or
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
            if any(type(key) is not str or not key for key in tool.scope_absent_is_violation):
                raise ValueError("invalid known-absence scope dimension")
            dimensions = tuple(schema.get("properties", {})) if tool.scope_dimensions is None else tuple(tool.scope_dimensions)
            if len(set(dimensions)) != len(dimensions) or any(type(k) is not str or not k for k in dimensions):
                raise ValueError("invalid registered resource dimensions")
            if not set(tool.scope_absent_is_violation) <= set(dimensions):
                raise ValueError("known-absence dimension is not registered")
            tool = replace(tool, scope_dimensions=dimensions, scope_absent_is_violation=tuple(tool.scope_absent_is_violation), arguments_schema=schema, reads=tuple(tool.reads),
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
        # Only trusted registration can add referenced resource objects. A
        # submitted field never becomes scope context by using a reserved name.
        resources.pop("__scope_references", None)
        if tool.scope is None:
            resources.pop("__primary_unknown", None)
        if tool.scope_references is not None:
            references = tool.scope_references(copy_json(arguments), view)
            if type(references) is not list or any(type(r) is not dict for r in references):
                raise ValueError("trusted referenced resources must be objects")
            if any(not set(r) <= set(tool.scope_dimensions) for r in references):
                raise ValueError("referenced resource has an unregistered dimension")
            if references:
                resources["__scope_references"] = copy_json(references)
        # Dimensions come from trusted registration, never a submitted key set.
        for key in tool.scope_dimensions:
            resources.setdefault(key, None)
        # Other projection context (e.g. claim for IR1) remains available, but
        # never creates additional scope dimensions.
        return copy_json(act), copy_json(resources)
