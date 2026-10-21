"""Read Claude's frozen expectations. No model code or outcome generation."""
from copy import deepcopy
import hashlib
import itertools
import json
from pathlib import Path
from zipfile import ZipFile

import yaml

ROOT = Path(__file__).parents[1] / "expected_traces"
BUNDLE = ROOT / "v0.2.1"
ZIP_HASH = "48ee6504ab3a0e278c8bd1725f4586463057c2671ce3ccdbeb32acf3db77856e"


def verify_bundle():
    pin = json.loads((ROOT / "PROVENANCE_v021.json").read_text())
    archive = BUNDLE / "taa_expected_traces_v0.2.1.zip"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ZIP_HASH or pin["zip_sha256"] != ZIP_HASH:
        raise ValueError("independently supplied zip changed")
    manifest = BUNDLE / "MANIFEST.sha256"
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != pin["manifest_sha256"]:
        raise ValueError("supplied manifest changed")
    expected = {"MANIFEST.sha256", archive.name}
    with ZipFile(archive) as z:
        for line in manifest.read_text().splitlines():
            sha, name = line.split("  ", 1)
            path = BUNDLE / name
            if ".." in Path(name).parts or Path(name).is_absolute():
                raise ValueError("invalid manifest path")
            if hashlib.sha256(path.read_bytes()).hexdigest() != sha or z.read("expected_traces_v0.2/" + name) != path.read_bytes():
                raise ValueError("source changed: " + name)
            expected.add(name)
    actual = {str(p.relative_to(BUNDLE)) for p in BUNDLE.rglob("*") if p.is_file()}
    if actual != expected:
        raise ValueError("unexpected/missing bundle files")


def world():
    verify_bundle()
    return yaml.safe_load((BUNDLE / "world_W0.yaml").read_text())


def cases():
    verify_bundle()
    results = []
    for path in sorted((BUNDLE / "traces").glob("*.yaml")):
        for parent in yaml.safe_load(path.read_text()):
            candidates = [deepcopy(parent)] if parent.get("steps") else []
            for variant in parent.get("variants", []):
                if variant["mode"] == "continue":
                    candidate = deepcopy(parent)
                    candidate.pop("final", None)
                    candidate["steps"] += deepcopy(variant.get("steps", []))
                    candidate.update({k: deepcopy(v) for k, v in variant.items() if k != "steps"})
                else:
                    candidate = deepcopy(variant)
                candidates.append(candidate)
            for candidate in candidates:
                params = candidate.get("parameters", {})
                choices = itertools.product(*(params[k] for k in params)) if params else [()]
                for values in choices:
                    label = candidate["id"] + ("[" + ",".join(map(str, values)) + "]" if params else "")
                    results.append({"id": label, "trace": deepcopy(candidate), "parameters": dict(zip(params, values)),
                                    "source": str(path.relative_to(ROOT))})
    return results
