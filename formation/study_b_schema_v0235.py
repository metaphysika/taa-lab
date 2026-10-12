"""Case-independent reply syntax from the existing, visible tool interface.

No case, answer key, permitted status, recipient, route, or option is consulted.
The null branch preserves the original neutral prompt's finish action.
"""
import copy
import re

from formation.clients import ClaudeChat
from formation.study_a import TOOL_SPECS


def reply_schema():
    branches = []
    for name, description in TOOL_SPECS.items():
        match = re.fullmatch(re.escape(name) + r"\(([^)]*)\): .+", description)
        if match is None:
            raise ValueError("existing tool signature is not recognized")
        parameters = [p.strip() for p in match.group(1).split(",")]
        branches.append({
            "type": "object",
            "properties": {
                "tool": {"type": "string", "const": name},
                "args": {
                    "type": "object",
                    "properties": {p: {"type": "string"} for p in parameters},
                    "required": parameters,
                    "additionalProperties": False,
                },
                "reason": {"type": "string"},
            },
            "required": ["tool", "args"],
            "additionalProperties": False,
        })
    branches.append({
        "type": "object",
        "properties": {
            "tool": {"type": "null"},
            "args": {"type": "object", "properties": {}, "additionalProperties": False},
            "reason": {"type": "string"},
        },
        "required": ["tool", "args"],
        "additionalProperties": False,
    })
    return {"anyOf": branches}


class StructuredClaudeChat(ClaudeChat):
    """Only add native JSON formatting; leave default thinking/effort intact."""

    def body(self, system, messages):
        body = super().body(system, messages)
        body["output_config"] = {"format": {
            "type": "json_schema", "schema": copy.deepcopy(reply_schema()),
        }}
        return body
