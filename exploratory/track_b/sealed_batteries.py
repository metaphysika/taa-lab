"""Separate sealed entry point for Track B VB and EB freight batteries.

Rules enforced here (A6.1, M2, M3):
- No `--seed` argument on the command line and no `seed_sha256` anywhere.
- Generates its own private 256-bit seed via `secrets.randbits(256)` and stores
  it ONLY inside the external output folder (`private_seed.txt`), OR reads an
  existing private seed from `--seed-file` located outside any git repository.
- Refuses any seed below 2^128 and every integer seed constant present in the
  repository.
- Refuses to write inside this checkout, its main repo (when in a worktree),
  or any path whose folder or any ancestor contains a `.git` file or directory.
- Refuses to write into a non-empty output folder.
- Prints and writes to `sealed_manifest.json` ONLY hashes and counts (never
  case text, subject family names, seed value, or seed hash).
"""
from __future__ import annotations

import argparse
import ast
import json
import os
from pathlib import Path
import secrets
import sys

from exploratory.track_b.batteries import (
    DEV_SEED,
    STUDY,
    VERSION,
    build_blind_packet,
    canonical_json_bytes,
    canonical_sha256,
    check_eb_factorial_balance,
    check_exclusions,
    check_family_disjointness,
    generate_eb,
    generate_vb,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MIN_SEALED_SEED = 1 << 128

# Known seed constants elsewhere in the repository plus dynamic scan of exploratory/track_b/.
_KNOWN_REPO_SEEDS = frozenset({
    0,
    1,
    42,
    DEV_SEED,
    247056,
    248017,
})


def _collect_repo_seed_constants() -> frozenset[int]:
    """Collect integer constants present in Track B / harness / K2 repo Python files."""
    found = set(_KNOWN_REPO_SEEDS)
    found.add(MIN_SEALED_SEED)
    scan_dirs = (
        REPO_ROOT / "exploratory" / "track_b",
        REPO_ROOT / "exploratory" / "step4_harness",
        REPO_ROOT / "exploratory" / "k2_kaggle",
    )
    py_files: list[Path] = []
    for d in scan_dirs:
        if d.is_dir():
            py_files.extend(sorted(d.glob("*.py")))
    tests_dir = REPO_ROOT / "tests"
    if tests_dir.is_dir():
        py_files.extend(sorted(tests_dir.glob("test_track_b_*.py")))
    for py_file in py_files:
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and type(node.value) is int:
                found.add(node.value)
    return frozenset(found)


def validate_private_seed(seed: int) -> int:
    """Validate that a sealed seed is >= 2^128 and not any repo seed constant."""
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("Private seed must be an integer")
    if seed < MIN_SEALED_SEED:
        raise ValueError("Refusing private seed below 2^128")
    if seed in _collect_repo_seed_constants():
        raise ValueError("Refusing seed constant present in the repository")
    return seed


def _generate_private_seed() -> int:
    repo_seeds = _collect_repo_seed_constants()
    while True:
        candidate = secrets.randbits(256)
        if candidate >= MIN_SEALED_SEED and candidate not in repo_seeds:
            return candidate


def _discover_repo_roots() -> list[Path]:
    """Return this checkout root plus any parent main-repo root for a git worktree."""
    roots: list[Path] = [REPO_ROOT.resolve()]
    dot_git = REPO_ROOT / ".git"
    if dot_git.is_file():
        text = dot_git.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            if line.lower().startswith("gitdir:"):
                raw_gitdir = line.split(":", 1)[1].strip()
                gitdir = (REPO_ROOT / raw_gitdir).resolve()
                for parent in (gitdir, *gitdir.parents):
                    if parent.name == ".git" and parent.parent.is_dir():
                        roots.append(parent.parent.resolve())
                        break
    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = os.path.normcase(os.path.realpath(str(root)))
        if key not in seen:
            seen.add(key)
            deduped.append(root)
    return deduped


def _is_within(candidate: str, root: str) -> bool:
    cand_norm = os.path.normcase(os.path.abspath(candidate))
    root_norm = os.path.normcase(os.path.abspath(root))
    try:
        return os.path.commonpath([cand_norm, root_norm]) == root_norm
    except ValueError:
        return False


def _has_git_entry(path: Path) -> bool:
    """Return True if path or any ancestor contains a .git file or directory."""
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return True
    return False


def assert_outside_repo(path_arg: Path | str) -> Path:
    """Resolve path_arg and raise ValueError if inside any git repo or worktree."""
    if not path_arg or not str(path_arg).strip():
        raise ValueError("Path is required and must be outside any git repository")
    raw_path = Path(path_arg).expanduser()
    abs_path = Path(os.path.abspath(str(raw_path)))
    real_path = Path(os.path.realpath(str(abs_path)))

    for root in _discover_repo_roots():
        root_real = os.path.realpath(str(root))
        root_abs = os.path.abspath(str(root))
        for candidate in (str(abs_path), str(real_path)):
            if _is_within(candidate, root_real) or _is_within(candidate, root_abs):
                raise ValueError(
                    f"Refusing path inside the repository: {path_arg!r}"
                )
        for parent in abs_path.parents:
            if parent.exists():
                parent_real = os.path.realpath(str(parent))
                if _is_within(parent_real, root_real):
                    raise ValueError(
                        f"Refusing path inside the repository: {path_arg!r}"
                    )
                break

    if _has_git_entry(abs_path) or _has_git_entry(real_path):
        raise ValueError(
            f"Refusing path inside a directory with a .git entry: {path_arg!r}"
        )
    return real_path


def _read_seed_file(seed_file: Path | str) -> int:
    resolved = assert_outside_repo(seed_file)
    if not resolved.is_file():
        raise FileNotFoundError(f"Seed file not found: {resolved}")
    raw = resolved.read_text(encoding="utf-8").strip()
    try:
        seed = int(raw, 0)
    except ValueError as exc:
        raise ValueError("Seed file must contain one integer (decimal or 0x hex)") from exc
    return validate_private_seed(seed)


def write_sealed_batteries(
    output_dir: Path | str,
    *,
    seed_file: Path | str | None = None,
) -> dict:
    """Generate VB and EB and write them to an empty folder outside any git repo.

    If `seed_file` is None, generates a fresh 256-bit seed via `secrets.randbits(256)`
    and saves it only to `<output_dir>/private_seed.txt`.
    Returns a public-safe manifest containing ONLY hashes and counts.
    """
    out = assert_outside_repo(output_dir)
    if out.exists():
        if not out.is_dir():
            raise ValueError(f"Output path exists and is not a directory: {output_dir!r}")
        if any(out.iterdir()):
            raise ValueError(f"Refusing to write sealed batteries into non-empty folder: {output_dir!r}")

    seed = _read_seed_file(seed_file) if seed_file is not None else _generate_private_seed()

    check_family_disjointness()
    vb_cases = generate_vb(seed)
    eb_data = generate_eb(seed)
    eb_cases = eb_data["cases"]
    eb_detached = eb_data["detached_items"]

    # Confirm VB and EB draws are strictly disjoint.
    vb_fams = {c["subject_family"] for c in vb_cases}
    eb_fams = {c["subject_family"] for c in eb_cases}
    if vb_fams & eb_fams:
        raise ValueError("VB and EB drew overlapping families")

    check_exclusions(vb_cases)
    check_exclusions(eb_cases, eb_detached)
    eb_cells = check_eb_factorial_balance(eb_cases)

    vb_packet, vb_map = build_blind_packet(vb_cases, seed, "TB-VB")
    eb_packet, eb_map = build_blind_packet(eb_cases, seed, "TB-EB")

    vb_payload = {
        "study": STUDY,
        "version": VERSION,
        "battery": "VB",
        "counts": {
            "total": len(vb_cases),
            "W": sum(c["kind"] == "W" for c in vb_cases),
            "U": sum(c["kind"] == "U" for c in vb_cases),
            "families": len(vb_fams),
            "direction_min_families": len({c["subject_family"] for c in vb_cases if c["threshold_direction"] == "min"}),
            "direction_max_families": len({c["subject_family"] for c in vb_cases if c["threshold_direction"] == "max"}),
        },
        "cases": vb_cases,
    }
    eb_payload = {
        "study": STUDY,
        "version": VERSION,
        "battery": "EB",
        "counts": {
            "total_cases": len(eb_cases),
            "W": sum(c["kind"] == "W" for c in eb_cases),
            "U": sum(c["kind"] == "U" for c in eb_cases),
            "detached_items": len(eb_detached),
            "families": len(eb_fams),
            "direction_min_families": len({c["subject_family"] for c in eb_cases if c["threshold_direction"] == "min"}),
            "direction_max_families": len({c["subject_family"] for c in eb_cases if c["threshold_direction"] == "max"}),
            "cells": eb_cells,
        },
        "cases": eb_cases,
        "detached_items": eb_detached,
    }

    artifacts = {
        "vb_cases.json": vb_payload,
        "eb_cases.json": eb_payload,
        "eb_detached.json": {
            "study": STUDY,
            "version": VERSION,
            "battery": "EB",
            "count": len(eb_detached),
            "detached_items": eb_detached,
        },
        "vb_blind_packet.json": vb_packet,
        "vb_blind_map.json": vb_map,
        "eb_blind_packet.json": eb_packet,
        "eb_blind_map.json": eb_map,
    }

    public_manifest = {
        "study": STUDY,
        "version": VERSION,
        "sealed": True,
        "counts": {
            "VB": vb_payload["counts"],
            "EB": eb_payload["counts"],
        },
        "sha256": {name: canonical_sha256(obj) for name, obj in artifacts.items()},
    }

    out.mkdir(parents=True, exist_ok=True)
    # Re-verify emptiness right before writing.
    if any(out.iterdir()):
        raise ValueError(f"Refusing to write sealed batteries into non-empty folder: {output_dir!r}")
    (out / "private_seed.txt").write_bytes(f"{seed}\n".encode("utf-8"))
    for name, obj in artifacts.items():
        (out / name).write_bytes(canonical_json_bytes(obj))
    (out / "sealed_manifest.json").write_bytes(canonical_json_bytes(public_manifest))
    return public_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate sealed Track B freight batteries (VB and EB) into an empty "
            "folder outside any git repository. Prints ONLY hashes and counts."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Empty external output folder outside any git repository.",
    )
    parser.add_argument(
        "--seed-file",
        type=Path,
        default=None,
        help=(
            "Optional path outside any git repository containing a private >= 2^128 "
            "integer seed. If omitted, a fresh 256-bit seed is generated via secrets."
        ),
    )
    args = parser.parse_args(argv)
    manifest = write_sealed_batteries(args.output_dir, seed_file=args.seed_file)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
