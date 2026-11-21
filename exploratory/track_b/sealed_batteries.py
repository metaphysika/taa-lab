"""Separate sealed entry point for Track B VB and EB freight batteries.

Rules enforced here:
- Requires an explicit private integer seed (no default seed lives in the repo).
- Strictly refuses to write anywhere inside the repository (including the main
  checkout when invoked from a git worktree, and symlink/relative paths).
- Prints and records in sealed_manifest.json ONLY hashes and counts (never raw
  case text, subject family names, or the raw private seed).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from exploratory.track_b.batteries import (
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
                # Worktree gitdir typically lives under <main-repo>/.git/worktrees/<name>.
                for parent in (gitdir, *gitdir.parents):
                    if parent.name == ".git" and parent.parent.is_dir():
                        roots.append(parent.parent.resolve())
                        break
    # Deduplicate while preserving order.
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
        # Different drive letters on Windows -> definitely outside.
        return False


def assert_outside_repo(output_dir: Path | str) -> Path:
    """Resolve output_dir and raise ValueError if it lies inside any repo root."""
    if not output_dir or not str(output_dir).strip():
        raise ValueError("output_dir is required and must be outside the repository")
    raw_path = Path(output_dir).expanduser()
    abs_path = Path(os.path.abspath(str(raw_path)))
    real_path = Path(os.path.realpath(str(abs_path)))

    for root in _discover_repo_roots():
        root_real = os.path.realpath(str(root))
        root_abs = os.path.abspath(str(root))
        for candidate in (str(abs_path), str(real_path)):
            if _is_within(candidate, root_real) or _is_within(candidate, root_abs):
                raise ValueError(
                    f"Refusing to write sealed batteries inside the repository: {output_dir!r}"
                )
        # Also verify no parent component of an existing path resolves inside the repo.
        for parent in abs_path.parents:
            if parent.exists():
                parent_real = os.path.realpath(str(parent))
                if _is_within(parent_real, root_real):
                    raise ValueError(
                        f"Refusing to write sealed batteries inside the repository: {output_dir!r}"
                    )
                break
    return real_path


def write_sealed_batteries(output_dir: Path | str, seed: int) -> dict:
    """Generate VB and EB with a private seed and write them outside the repo.

    Returns a public-safe manifest containing ONLY hashes and counts (no case
    text, no subject family names, and no raw seed).
    """
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("A private integer seed is required for VB and EB")
    out = assert_outside_repo(output_dir)

    check_family_disjointness()
    vb_cases = generate_vb(seed)
    eb_data = generate_eb(seed)
    eb_cases = eb_data["cases"]
    eb_detached = eb_data["detached_items"]

    check_exclusions(vb_cases)
    check_exclusions(eb_cases, eb_detached)
    eb_cells = check_eb_factorial_balance(eb_cases)

    vb_packet, vb_map = build_blind_packet(vb_cases, seed ^ 0x5B11D, "TB-VB")
    eb_packet, eb_map = build_blind_packet(eb_cases, seed ^ 0xEB11D, "TB-EB")

    vb_payload = {
        "study": STUDY,
        "version": VERSION,
        "battery": "VB",
        "counts": {
            "total": len(vb_cases),
            "W": sum(c["kind"] == "W" for c in vb_cases),
            "U": sum(c["kind"] == "U" for c in vb_cases),
            "families": len({c["subject_family"] for c in vb_cases}),
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
            "families": len({c["subject_family"] for c in eb_cases}),
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

    seed_sha256 = hashlib.sha256(f"{VERSION}:sealed-seed:{seed}".encode("utf-8")).hexdigest()
    public_manifest = {
        "study": STUDY,
        "version": VERSION,
        "sealed": True,
        "seed_sha256": seed_sha256,
        "counts": {
            "VB": vb_payload["counts"],
            "EB": eb_payload["counts"],
        },
        "sha256": {name: canonical_sha256(obj) for name, obj in artifacts.items()},
    }

    out.mkdir(parents=True, exist_ok=True)
    for name, obj in artifacts.items():
        (out / name).write_bytes(canonical_json_bytes(obj))
    (out / "sealed_manifest.json").write_bytes(canonical_json_bytes(public_manifest))
    return public_manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate sealed Track B freight batteries (VB and EB) outside the repository. "
            "Prints ONLY hashes and counts."
        )
    )
    parser.add_argument(
        "--seed",
        type=int,
        required=True,
        help="Private integer seed (not stored in the repository).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="External output folder outside the repository.",
    )
    args = parser.parse_args(argv)
    manifest = write_sealed_batteries(args.output_dir, args.seed)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
