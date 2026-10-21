"""Read frozen source bytes, never synthesize or rewrite expected outcomes."""
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
import re
from zipfile import ZipFile

import yaml

ROOT = Path(__file__).parents[1] / "expected_traces"
BUNDLE = ROOT / "v0.1"
ZIP_HASH = "e6ee4e2683f908e7c008b926db801886f836b2c6a25fe8ee81fd355f04d1939e"


def verify_bundle():
    pin = json.loads((ROOT / "PROVENANCE_v01.json").read_text())
    archive = BUNDLE / "taa_expected_traces_v0.1.zip"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ZIP_HASH or pin["zip_sha256"] != ZIP_HASH:
        raise ValueError("the independently supplied zip changed")
    manifest = BUNDLE / "MANIFEST.sha256"
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != pin["manifest_sha256"]:
        raise ValueError("the supplied manifest changed")
    expected = {"MANIFEST.sha256", archive.name}
    with ZipFile(archive) as zip_file:
        for line in manifest.read_text().splitlines():
            sha, name = line.split("  ", 1)
            path = BUNDLE / name
            if ".." in Path(name).parts or Path(name).is_absolute():
                raise ValueError("invalid manifest path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
                raise ValueError("expected source changed: " + name)
            if zip_file.read("expected_traces_v0/" + name) != path.read_bytes():
                raise ValueError("extracted bytes differ from source zip")
            expected.add(name)
    actual = {str(path.relative_to(BUNDLE)) for path in BUNDLE.rglob("*") if path.is_file()}
    if actual != expected:
        raise ValueError("unexpected/missing files in the frozen bundle")


def _yaml_text(text):
    """Quote unquoted D_refund(...) identifiers in memory; source is untouched.

    YAML flow commas otherwise turn D_refund(CL1,120) into two values/keys.
    No numbers, assertions, questions or quoted/comment text are changed.
    This lexical mapping is explicitly pending Claude's mapping review.
    """
    output = []
    quote = None
    i = 0
    while i < len(text):
        char = text[i]
        if quote:
            output.append(char)
            if char == "\\" and quote == '"' and i + 1 < len(text):
                i += 1
                output.append(text[i])
            elif char == quote:
                if quote == "'" and i + 1 < len(text) and text[i + 1] == "'":
                    i += 1
                    output.append(text[i])
                else:
                    quote = None
        elif char == "#":
            end = text.find("\n", i)
            end = len(text) if end < 0 else end
            output.append(text[i:end])
            i = end
            continue
        elif char in ('"', "'") and (i == 0 or not text[i - 1].isalnum()):
            quote = char
            output.append(char)
        elif text.startswith("D_refund(", i):
            end = text.find(")", i)
            if end < 0:
                raise ValueError("unterminated abstract duty identifier")
            output.append(json.dumps(text[i:end + 1]))
            i = end
        else:
            output.append(char)
        i += 1
    return "".join(output)


def _pending_nodes(node, lines, path=()):
    found = {}
    if isinstance(node, yaml.ScalarNode):
        line = lines[node.start_mark.line]
        # The supplied comments identify Q3 and Q5 dependencies even where the
        # scalar is a concrete name/status. Do not skip neighboring assertions.
        match = re.search(r"pending_spec\(Q([1-9])\)", node.value)
        comment = line.split("#", 1)[1] if "#" in line else ""
        marked = re.search(r"pending_spec(?:\(|\s+)Q([1-9])\)?", comment)
        if match or marked:
            found[path] = "Q" + (match or marked).group(1)
    elif isinstance(node, yaml.SequenceNode):
        for index, child in enumerate(node.value):
            found.update(_pending_nodes(child, lines, path + (index,)))
    elif isinstance(node, yaml.MappingNode):
        for key, child in node.value:
            found.update(_pending_nodes(child, lines, path + (key.value,)))
    return found


def read_yaml(path):
    text = _yaml_text(path.read_text())
    tree = yaml.compose(text, Loader=yaml.SafeLoader)
    return yaml.safe_load(text), _pending_nodes(tree, text.splitlines())


def world():
    verify_bundle()
    return read_yaml(BUNDLE / "world_W0.yaml")[0]


def cases():
    verify_bundle()
    plan = json.loads((ROOT / "INPUT_PLAN_v01.json").read_text())
    results = []
    for path in sorted((BUNDLE / "traces").glob("*.yaml")):
        traces, pending = read_yaml(path)
        for index, trace in enumerate(traces):
            # A container with variants but no steps (T36) is not a vacuous pass.
            candidates = []
            if trace.get("steps"):
                candidates.append((trace, (index,), None))
            for vindex, variant in enumerate(trace.get("variants", [])):
                mode = plan[variant["id"]]
                combined = deepcopy(trace)
                combined.pop("variants", None)
                combined.update({k: deepcopy(v) for k, v in variant.items() if k not in ("steps", "setup")})
                combined["setup"] = deepcopy(variant.get("setup", trace.get("setup", {})))
                combined["steps"] = deepcopy((trace.get("steps", []) if mode["steps"] == "append" else []) + variant.get("steps", []))
                # A variant's final block is inherited only for append variants.
                if mode["steps"] == "replace" and "final" not in variant:
                    combined.pop("final", None)
                candidates.append((combined, (index, "variants", vindex), trace if mode["steps"] == "append" else None))
            for candidate, prefix, base in candidates:
                params = candidate.get("parameters", {})
                choices = itertools.product(*(params[k] for k in params)) if params else [()]
                for values in choices:
                    data = deepcopy(candidate)
                    parameters = dict(zip(params, values))
                    case_id = data["id"] + ("[" + ",".join(str(v) for v in values) + "]" if params else "")
                    # Keep expectation objects as supplied; only simulator input
                    # parameters are substituted later by the runner.
                    selected_pending = {key[len(prefix):]: value for key, value in pending.items() if key[:len(prefix)] == prefix}
                    if base:
                        base_prefix = (index,)
                        base_steps = len(base.get("steps", []))
                        merged = {key[len(base_prefix):]: value for key, value in pending.items()
                                  if key[:len(base_prefix)] == base_prefix and len(key) > 1 and key[1] != "variants"}
                        for key, value in selected_pending.items():
                            if key and key[0] == "steps":
                                key = ("steps", key[1] + base_steps) + key[2:]
                            merged[key] = value
                        selected_pending = merged
                    results.append({"id": case_id, "trace": data, "parameters": parameters,
                                    "pending": selected_pending, "source": str(path.relative_to(ROOT))})
    return results
