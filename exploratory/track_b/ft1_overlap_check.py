"""Custodian-only FT1-overlap attestation script for Track B freight batteries.

Run ONLY by FT1 sealed-material custodians (Sol or Astra).
This module NEVER imports exploratory.ft1.sealed and NEVER reads any FT1 files
unless explicit paths are supplied by the custodian at invocation time.

Matching rules (Round 2 M1 + S1):
- Parses JSON / JSONL strictly; fails with a clear ValueError on non-JSON input.
- Extracts all string values from any JSON record shape (including `messages`
  lists, case dicts, nested lists/dicts) and excludes JSON key names from text.
- Subtracts harness boilerplate stems derived from template cases across all
  issuers/pushes plus all JSON key stems from both sides.
- Stem-matches ONLY `family_id`, `cargo_noun`, and `metric_label`.
- Matches `keywords` ONLY as whole words (never stemmed) and only when not
  everyday English / boilerplate words.
- Bases `NOT_ESTABLISHED` (exit code 2) on `ft1_content_stem_count < 50`.
- Outputs ONLY an attestation (`NO_OVERLAP` | `OVERLAP_FOUND` | `NOT_ESTABLISHED`),
  counts, and input SHA-256 digests (no subject names or text). Optional
  `--detail-out` writes custodian-only match details strictly outside any repo.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

from exploratory.track_b.batteries import (
    ALL_SUBJECT_FAMILIES,
    DEV_DIR,
    DISJOINTNESS_ALLOWLIST,
    EXCLUDED_PATTERNS,
    EXCLUDED_THEMES,
    FAMILIES_BY_BATTERY,
    ISSUERS,
    PUSHES,
    SubjectFamily,
    build_case,
    build_detached_item,
    content_stems,
    family_core_stems,
    file_sha256,
)
from exploratory.track_b.sealed_batteries import assert_outside_repo

MIN_FT1_CONTENT_STEMS = 50

# Everyday English words excluded from whole-word keyword matching (M1).
_EVERYDAY_KEYWORDS = frozenset({
    "anchor", "bark", "belt", "blade", "bleed", "break", "cable", "channel",
    "clearing", "coating", "concrete", "curl", "decay", "dial", "dust", "echo",
    "efficiency", "fade", "felt", "fence", "fiber", "filter", "flame", "flash",
    "flatness", "fleece", "flow", "fog", "foil", "grain", "hay", "hiding",
    "hold", "housing", "impact", "insert", "lamp", "lantern", "light", "lump",
    "magnet", "mesh", "oak", "odor", "packing", "paving", "peel", "pine",
    "plate", "pore", "pulse", "rim", "roadway", "sag", "sap", "screen",
    "scrub", "seed", "sheen", "solar", "speed", "spill", "sponge", "sprout",
    "strap", "stretch", "sweep", "syrup", "tack", "terminal", "thickness",
    "timber", "tread", "vest", "visibility", "void", "wash", "wrap", "yield",
})

_EXTRA_KEY_BOILERPLATE = frozenset({
    "json", "tool", "args", "reason", "answer", "permissible", "messages",
    "role", "content", "assistant", "user", "system", "prompt", "seed",
    "version", "study", "battery", "cases", "counts", "manifest", "sha256",
    "detached", "items", "theme", "subject", "family", "pair", "base",
    "kind", "issuer", "push", "pressure", "rung", "gate", "counsel",
    "warrant", "world", "records", "shipments", "questions", "humans",
    "roster", "staff", "deciding", "evidence", "rationale", "recipient",
    "requested", "preserved", "status", "difficulty", "group", "direct",
})


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def _collect_strings_and_keys(obj: object) -> tuple[list[str], set[str]]:
    """Collect all string values and all dict key names from any JSON structure."""
    strings: list[str] = []
    keys: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, str):
            strings.append(node)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str):
                    keys.add(k)
                walk(v)

    walk(obj)
    return strings, keys


def _build_harness_boilerplate_stems() -> frozenset[str]:
    """Derive harness boilerplate stems from a placeholder template case across all arms."""
    placeholder_tokens = {"zxqv", "plchld", "wdgt", "mtrc", "untq", "cdname"}
    placeholder_fam = SubjectFamily(
        family_id="zxqv_plchld",
        battery="MB",
        cargo_noun="zxqv wdgt",
        record_source="Authenticated laboratory inspection test record",
        metric_label="zxqv mtrc",
        unit="untq",
        direction="max",
        threshold=99.0,
        precision=1,
        rule_text="Post RELEASED only if zxqv mtrc is at most 99.0 untq.",
        fail_range=(110.0, 120.0),
        pass_range=(50.0, 60.0),
        keywords=("zxqv",),
    )
    stems: set[str] = set()
    for issuer in ISSUERS:
        for push in PUSHES:
            for kind in ("W", "U"):
                case = build_case(
                    case_id="TB-TPL-01",
                    battery="MB",
                    family=placeholder_fam,
                    title="zxqv wdgt cdname",
                    kind=kind,
                    pair_id="TB-TPL",
                    base_case_id="TB-TPL",
                    recipient="Inez",
                    measurement_value=115.0 if kind == "W" else 55.0,
                    issuer=issuer,
                    push=push,
                )
                det = build_detached_item(case)
                for obj in (case, det):
                    strings, keys = _collect_strings_and_keys(obj)
                    for s in strings:
                        stems.update(content_stems(s))
                    for k in keys:
                        stems.update(content_stems(k.replace("_", " ")))
    # Also include min-direction phrasing ("at least") and extra structural boilerplate.
    stems.update(content_stems("Post RELEASED only if at least at most"))
    for word in _EXTRA_KEY_BOILERPLATE:
        stems.update(content_stems(word))
    # Remove any stems originating from the invented placeholder tokens themselves.
    for pt in placeholder_tokens:
        stems.difference_update(content_stems(pt))
    return frozenset(stems)


HARNESS_BOILERPLATE_STEMS: frozenset[str] = _build_harness_boilerplate_stems()


def _collect_input_files(paths: list[Path]) -> list[Path]:
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
    """Extract case-like dicts when present (used for optional case/theme counting)."""
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            if "case" in node and isinstance(node["case"], dict):
                walk(node["case"])
                return
            if any(k in node for k in ("theme", "subject_family", "deciding_evidence", "task", "messages")):
                found.append(node)
                return
            for key in ("cases", "items", "records", "episodes", "batteries"):
                if key in node:
                    walk(node[key])

    walk(obj)
    return found


def _parse_json_file(fpath: Path) -> list[object]:
    """Parse .json or .jsonl strictly; fail with a clear ValueError on non-JSON input."""
    text = fpath.read_text(encoding="utf-8")
    stripped = text.strip()
    if not stripped:
        raise ValueError(f"Non-JSON input in {fpath.name}: file is empty")
    if fpath.suffix.lower() == ".jsonl":
        parsed: list[object] = []
        for lineno, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Non-JSON input in {fpath.name} line {lineno}: {exc.msg}"
                ) from exc
        if not parsed:
            raise ValueError(f"Non-JSON input in {fpath.name}: no JSON lines found")
        return parsed
    try:
        return [json.loads(text)]
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Non-JSON input in {fpath.name}: {exc.msg} (line {exc.lineno}, col {exc.colno})"
        ) from exc


def _load_files(
    files: list[Path],
) -> tuple[list[dict], list[str], set[str], dict[str, str]]:
    """Return (case_like_records, all_string_values, all_json_keys, file_hashes)."""
    records: list[dict] = []
    strings: list[str] = []
    keys: set[str] = set()
    hashes: dict[str, str] = {}
    for idx, fpath in enumerate(files, start=1):
        label = f"{idx:03d}:{fpath.name}"
        hashes[label] = file_sha256(fpath)
        objs = _parse_json_file(fpath)
        for obj in objs:
            records.extend(_extract_case_dicts(obj))
            s_vals, k_vals = _collect_strings_and_keys(obj)
            strings.extend(s_vals)
            keys.update(k_vals)
    return records, strings, keys, hashes


def _case_text(case: dict) -> str:
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
        text = _case_text(case)
        for _, pat in EXCLUDED_PATTERNS:
            if pat.search(text):
                hits += 1
    return hits


def _distinctive_keywords(fam: SubjectFamily) -> tuple[str, ...]:
    """Keep only non-everyday, non-boilerplate whole-word keywords (M1)."""
    kept: list[str] = []
    for kw in fam.keywords:
        low = kw.lower().strip()
        if (
            len(low) < 4
            or low in _EVERYDAY_KEYWORDS
            or low in DISJOINTNESS_ALLOWLIST
            or low in _EXTRA_KEY_BOILERPLATE
        ):
            continue
        if content_stems(low).issubset(HARNESS_BOILERPLATE_STEMS):
            continue
        kept.append(low)
    return tuple(kept)


def compute_overlap_attestation(
    ft1_paths: list[Path | str],
    dev_dir: Path | str | None = DEV_DIR,
    sealed_dir: Path | str | None = None,
    detail_out: Path | str | None = None,
) -> dict:
    """Compare Track B subject families against FT1 sealed files (M1/S1).

    Returns ONLY an attestation (`NO_OVERLAP` | `OVERLAP_FOUND` | `NOT_ESTABLISHED`)
    with counts and SHA-256 digests. Zero subject names, keywords, or case texts
    are returned. If `detail_out` is provided, it must lie outside any git repo
    and receives custodian-only diagnostic match details.
    """
    if detail_out is not None:
        detail_path = assert_outside_repo(detail_out)
    else:
        detail_path = None

    ft1_files = _collect_input_files([Path(p) for p in ft1_paths])
    ft1_records, ft1_strings, ft1_keys, ft1_hashes = _load_files(ft1_files)

    ft1_key_stems: set[str] = set()
    for k in ft1_keys:
        ft1_key_stems.update(content_stems(k.replace("_", " ")))

    subtracted_stems = HARNESS_BOILERPLATE_STEMS | ft1_key_stems

    ft1_themes: set[str] = set()
    for rec in ft1_records:
        for key in ("theme", "subject_family"):
            val = rec.get(key)
            if isinstance(val, str) and val.strip():
                ft1_themes.add(_norm(val))

    ft1_norm_strings: list[str] = []
    ft1_words: set[str] = set()
    ft1_content_stems: set[str] = set()
    for s in ft1_strings:
        norm_s = _norm(s)
        if not norm_s:
            continue
        ft1_norm_strings.append(norm_s)
        ft1_words.update(re.findall(r"[a-z0-9]+", s.lower()))
        ft1_content_stems.update(content_stems(s) - subtracted_stems)

    # Load optional concrete Track B dev/sealed files for SHA-256 binding and exclusion checks.
    tb_files: list[Path] = []
    if dev_dir is not None and Path(dev_dir).exists():
        tb_files.extend(
            p for p in sorted(Path(dev_dir).glob("*_cases.json")) if p.is_file()
        )
    if sealed_dir is not None and Path(sealed_dir).exists():
        tb_files.extend(
            p for p in sorted(Path(sealed_dir).glob("*_cases.json")) if p.is_file()
        )
    tb_cases, _, _, tb_hashes = _load_files(tb_files) if tb_files else ([], [], set(), {})

    exact_theme_overlaps = 0
    phrase_overlaps = 0
    stem_overlaps = 0
    keyword_overlaps = 0
    per_group_overlaps: dict[str, int] = {g: 0 for g in FAMILIES_BY_BATTERY}
    detail_rows: list[dict] = []

    for fam in ALL_SUBJECT_FAMILIES:
        fam_matched = False
        reasons: list[str] = []

        # 1. Exact family_id match against theme/subject_family fields.
        fam_id_norm = _norm(fam.family_id)
        if fam_id_norm in ft1_themes or fam.family_id.lower() in ft1_themes:
            exact_theme_overlaps += 1
            fam_matched = True
            reasons.append("exact_theme")

        # 2. Whole-phrase match on cargo_noun and metric_label.
        p_hit = False
        for phrase in (fam.cargo_noun, fam.metric_label):
            p_norm = _norm(phrase)
            if " " in p_norm:
                pat = re.compile(r"\b" + re.escape(p_norm) + r"\b")
                if any(pat.search(t) for t in ft1_norm_strings):
                    p_hit = True
                    break
        if p_hit:
            phrase_overlaps += 1
            fam_matched = True
            reasons.append("phrase")

        # 3. Stemmed match ONLY on family_id, cargo_noun, metric_label (minus boilerplate & keys).
        core_stems = family_core_stems(fam) - subtracted_stems
        shared_stems = sorted(core_stems & ft1_content_stems)
        if shared_stems:
            stem_overlaps += 1
            fam_matched = True
            reasons.append("core_stem")

        # 4. Whole-word match on distinctive non-everyday keywords only (never stemmed).
        matched_kws: list[str] = []
        for kw in _distinctive_keywords(fam):
            if " " in kw:
                pat = re.compile(r"\b" + re.escape(_norm(kw)) + r"\b")
                if any(pat.search(t) for t in ft1_norm_strings):
                    matched_kws.append(kw)
            elif kw in ft1_words:
                matched_kws.append(kw)
        if matched_kws:
            keyword_overlaps += 1
            fam_matched = True
            reasons.append("keyword")

        if fam_matched:
            per_group_overlaps[fam.battery] += 1
            detail_rows.append({
                "group": fam.battery,
                "family_id": fam.family_id,
                "match_kinds": reasons,
                "shared_core_stems": shared_stems,
                "matched_keywords": matched_kws,
            })

    exclusion_hits = _track_b_exclusion_hits(tb_cases)
    ft1_content_stem_count = len(ft1_content_stems)

    if ft1_content_stem_count < MIN_FT1_CONTENT_STEMS:
        attestation = "NOT_ESTABLISHED"
        overlap_detected = None
    else:
        overlap_detected = (
            exact_theme_overlaps > 0
            or phrase_overlaps > 0
            or stem_overlaps > 0
            or keyword_overlaps > 0
            or exclusion_hits > 0
        )
        attestation = "OVERLAP_FOUND" if overlap_detected else "NO_OVERLAP"

    result = {
        "attestation": attestation,
        "overlap_detected": overlap_detected,
        "track_b_groups_checked": list(FAMILIES_BY_BATTERY.keys()),
        "track_b_family_count": len(ALL_SUBJECT_FAMILIES),
        "track_b_case_count": len(tb_cases),
        "ft1_file_count": len(ft1_files),
        "ft1_case_count": len(ft1_records),
        "ft1_theme_count": len(ft1_themes),
        "ft1_content_stem_count": ft1_content_stem_count,
        "min_ft1_content_stems": MIN_FT1_CONTENT_STEMS,
        "exact_theme_overlap_count": exact_theme_overlaps,
        "phrase_overlap_count": phrase_overlaps,
        "stemmed_token_overlap_count": stem_overlaps,
        "keyword_overlap_count": keyword_overlaps,
        "exclusion_list_overlap_count": exclusion_hits,
        "per_group_overlap_counts": per_group_overlaps,
        "track_b_inputs_sha256": tb_hashes,
        "ft1_inputs_sha256": ft1_hashes,
    }

    if detail_path is not None:
        detail_path.parent.mkdir(parents=True, exist_ok=True)
        detail_payload = {
            "attestation": attestation,
            "ft1_content_stem_count": ft1_content_stem_count,
            "matches": detail_rows,
        }
        detail_path.write_bytes(
            (json.dumps(detail_payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        )

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Custodian-only FT1 overlap attestation for Track B freight batteries. "
            "Outputs ONLY a yes/no/NOT_ESTABLISHED attestation with counts."
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
        help="Optional path to write the sanitized attestation JSON.",
    )
    parser.add_argument(
        "--detail-out",
        type=Path,
        default=None,
        help="Optional custodian-only detail JSON path (must lie outside any git repo).",
    )
    args = parser.parse_args(argv)
    try:
        result = compute_overlap_attestation(
            ft1_paths=args.ft1_path,
            dev_dir=args.track_b_dev_dir,
            sealed_dir=args.track_b_sealed_dir,
            detail_out=args.detail_out,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(rendered.encode("utf-8"))
    print(rendered, end="")
    return 2 if result["attestation"] == "NOT_ESTABLISHED" else 0


if __name__ == "__main__":
    sys.exit(main())
