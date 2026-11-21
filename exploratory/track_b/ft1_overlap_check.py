"""Custodian-only FT1-overlap attestation script for Track B freight batteries.

Run ONLY by FT1 sealed-material custodians (Sol or Astra).
This module NEVER imports exploratory.ft1.sealed and NEVER reads any FT1 files
unless explicit paths are supplied by the custodian at invocation time.

It compares Track B subject families (MB, PB, LD, VB, EB) against the supplied
FT1 sealed case files and outputs ONLY a yes/no attestation with counts and
input file SHA-256 hashes (no FT1 or VB/EB case text or subject names).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from exploratory.track_b.batteries import (
    DEV_DIR,
    EXCLUDED_PATTERNS,
    EXCLUDED_THEMES,
    FAMILIES_BY_BATTERY,
    SUBJECT_FAMILIES,
    file_sha256,
)

# Common freight-harness boilerplate tokens ignored during keyword-overlap checks.
_BOILERPLATE_TOKENS = frozenset({
    "authenticated", "record", "laboratory", "quality", "control", "inspection",
    "current", "final", "result", "post", "released", "only", "most", "least",
    "percent", "standard", "primary", "cargo", "routine", "order", "issue",
    "manager", "driver", "report", "company", "rule", "evidence", "source",
    "status", "pending", "batch", "crate", "pallet", "carton", "bundle", "drum",
    "roll", "sack", "tote", "tray", "case", "lot", "box", "bag", "coil", "keg",
    "vat", "canister", "bale", "stack", "bolt", "carboy", "tin", "slab",
    "reading", "rating", "value", "share", "rate", "load", "force", "mass",
    "strength", "ratio", "level", "content", "limit", "grade", "per",
})


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _tokens(text: str) -> set[str]:
    return {
        tok
        for tok in re.findall(r"[a-z0-9]+", text.lower())
        if len(tok) >= 4 and tok not in _BOILERPLATE_TOKENS and not tok.isdigit()
    }


def _collect_json_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        if not path.exists():
            raise FileNotFoundError(f"Input path does not exist: {path}")
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file() and child.suffix.lower() in (".json", ".jsonl"):
                    files.append(child)
    if not files:
        raise ValueError("No .json or .jsonl files found in supplied paths")
    return files


def _extract_case_dicts(obj: object) -> list[dict]:
    """Extract case-like dicts from common freight JSON/JSONL containers."""
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            if "case" in node and isinstance(node["case"], dict):
                walk(node["case"])
                return
            if any(k in node for k in ("theme", "subject_family", "deciding_evidence", "task")):
                found.append(node)
                return
            for key in ("cases", "items", "records", "episodes", "batteries"):
                if key in node:
                    walk(node[key])

    walk(obj)
    return found


def _load_cases_from_files(files: list[Path]) -> tuple[list[dict], dict[str, str]]:
    cases: list[dict] = []
    hashes: dict[str, str] = {}
    for idx, fpath in enumerate(files, start=1):
        label = f"{idx:03d}:{fpath.name}"
        hashes[label] = file_sha256(fpath)
        if fpath.suffix.lower() == ".jsonl":
            for line in fpath.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                cases.extend(_extract_case_dicts(json.loads(line)))
        else:
            cases.extend(_extract_case_dicts(json.loads(fpath.read_text(encoding="utf-8"))))
    return cases, hashes


def _ft1_case_text(case: dict) -> str:
    parts = [
        str(case.get("theme", "")),
        str(case.get("subject_family", "")),
        str(case.get("title", "")),
        str(case.get("deciding_evidence", "")),
        str(case.get("task", "")),
    ]
    rec = (case.get("world") or {}).get("records") or {}
    if isinstance(rec, dict):
        primary = rec.get("PRIMARY")
        if isinstance(primary, dict):
            parts.append(str(primary.get("independent_evidence", "")))
            parts.append(str(primary.get("release_rule", "")))
    return " ".join(parts)


def _track_b_exclusion_hits(cases: list[dict]) -> int:
    hits = 0
    for case in cases:
        for field in ("theme", "subject_family"):
            if str(case.get(field, "")).lower() in EXCLUDED_THEMES:
                hits += 1
        text = _ft1_case_text(case)
        for _, pat in EXCLUDED_PATTERNS:
            if pat.search(text):
                hits += 1
    return hits


def compute_overlap_attestation(
    ft1_paths: list[Path | str],
    dev_dir: Path | str | None = DEV_DIR,
    sealed_dir: Path | str | None = None,
) -> dict:
    """Compare Track B subject families against FT1 sealed files.

    Returns ONLY a yes/no attestation with counts and SHA-256 digests.
    Zero subject names, keywords, or case texts are returned.
    """
    ft1_files = _collect_json_files([Path(p) for p in ft1_paths])
    ft1_cases, ft1_hashes = _load_cases_from_files(ft1_files)

    ft1_themes: set[str] = set()
    ft1_texts_norm: list[str] = []
    ft1_all_tokens: set[str] = set()
    for case in ft1_cases:
        for key in ("theme", "subject_family"):
            val = str(case.get(key, "")).strip()
            if val:
                ft1_themes.add(_norm(val))
        text = _ft1_case_text(case)
        ft1_texts_norm.append(_norm(text))
        ft1_all_tokens.update(_tokens(text))

    # Optionally load concrete Track B files for SHA-256 binding and exclusion checks.
    tb_files: list[Path] = []
    if dev_dir is not None and Path(dev_dir).exists():
        tb_files.extend(
            p for p in sorted(Path(dev_dir).glob("*_cases.json")) if p.is_file()
        )
    if sealed_dir is not None and Path(sealed_dir).exists():
        tb_files.extend(
            p for p in sorted(Path(sealed_dir).glob("*_cases.json")) if p.is_file()
        )
    tb_cases, tb_hashes = _load_cases_from_files(tb_files) if tb_files else ([], {})

    exact_theme_overlaps = 0
    keyword_overlaps = 0
    per_battery_overlaps: dict[str, int] = {b: 0 for b in ("MB", "PB", "LD", "VB", "EB")}

    for fam in SUBJECT_FAMILIES:
        fam_matched = False
        fam_id_norm = _norm(fam.family_id)
        if fam_id_norm in ft1_themes or fam.family_id.lower() in ft1_themes:
            exact_theme_overlaps += 1
            fam_matched = True

        # Check multi-word paraphrase phrases and distinctive single-word keywords.
        kw_hit = False
        for kw in fam.keywords:
            kw_norm = _norm(kw)
            if not kw_norm:
                continue
            if " " in kw_norm:
                pat = re.compile(r"\b" + re.escape(kw_norm) + r"\b")
                if any(pat.search(t) for t in ft1_texts_norm):
                    kw_hit = True
                    break
            else:
                if kw_norm in ft1_all_tokens or kw_norm in ft1_themes:
                    kw_hit = True
                    break
        if kw_hit:
            keyword_overlaps += 1
            fam_matched = True

        if fam_matched:
            per_battery_overlaps[fam.battery] += 1

    exclusion_hits = _track_b_exclusion_hits(tb_cases)
    overlap_detected = (
        exact_theme_overlaps > 0 or keyword_overlaps > 0 or exclusion_hits > 0
    )

    return {
        "attestation": "OVERLAP_FOUND" if overlap_detected else "NO_OVERLAP",
        "overlap_detected": overlap_detected,
        "track_b_batteries_checked": list(FAMILIES_BY_BATTERY.keys()),
        "track_b_family_count": len(SUBJECT_FAMILIES),
        "track_b_case_count": len(tb_cases),
        "ft1_file_count": len(ft1_files),
        "ft1_case_count": len(ft1_cases),
        "ft1_theme_count": len(ft1_themes),
        "exact_theme_overlap_count": exact_theme_overlaps,
        "keyword_overlap_count": keyword_overlaps,
        "exclusion_list_overlap_count": exclusion_hits,
        "per_battery_overlap_counts": per_battery_overlaps,
        "track_b_inputs_sha256": tb_hashes,
        "ft1_inputs_sha256": ft1_hashes,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Custodian-only FT1 overlap attestation for Track B freight batteries. "
            "Outputs ONLY a yes/no attestation with counts."
        )
    )
    parser.add_argument(
        "--ft1-path",
        action="append",
        required=True,
        type=Path,
        help="Path to an FT1 sealed JSON/JSONL file or directory (repeatable).",
    )
    parser.add_argument(
        "--track-b-dev-dir",
        type=Path,
        default=DEV_DIR,
        help="Track B development batteries directory.",
    )
    parser.add_argument(
        "--track-b-sealed-dir",
        type=Path,
        default=None,
        help="Optional external directory containing generated VB/EB sealed batteries.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Optional path to write the attestation JSON.",
    )
    args = parser.parse_args(argv)
    result = compute_overlap_attestation(
        ft1_paths=args.ft1_path,
        dev_dir=args.track_b_dev_dir,
        sealed_dir=args.track_b_sealed_dir,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(rendered.encode("utf-8"))
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
