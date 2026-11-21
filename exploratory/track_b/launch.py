"""Offline staging and receipt-bound launch for one Track B B0a candidate."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from exploratory.k2_kaggle import core

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = Path("C:/t/trackb/")
DATASET_COMPONENT = re.compile("[a-z0-9_-]+")
STATUS_TIMEOUT_SECONDS = 60
RECEIPT_FIELDS = {
    "schema_version", "stage", "commit_sha", "approval_id", "approval_text",
    "bundle_sha256", "adapter_dataset_id", "adapter_sha256", "created_utc",
}
ACTIVE = {"queued", "preparing", "running"}
TERMINAL = {"complete", "error", "cancelled", "canceled"}
KAGGLE_TIMEOUT_SECONDS = 10800
NOTEBOOK = "trackb.ipynb"
METADATA = "kernel-metadata.json"
BINDING = "binding.json"
DRAFT = "receipt-draft.json"
BUNDLE_FILES = (NOTEBOOK, METADATA, BINDING)

# Named FT1 source dependencies only. The B0a archive contains development data.
SOURCE_PATHS = (
    "agents", "taa", "world", "formation",
    "exploratory/step4_harness", "exploratory/step4_cases/drafts.py",
    "exploratory/measurement_v02456", "exploratory/k2_kaggle",
    "exploratory/track_b/__init__.py", "exploratory/track_b/batteries.py",
    "exploratory/track_b/verdict.py", "exploratory/track_b/training.py",
    "exploratory/track_b/launch.py", "exploratory/track_b/stage_b0a.py",
    "exploratory/track_b/dev_batteries/manifest.json",
    "exploratory/track_b/dev_batteries/mb_cases.json",
    "exploratory/track_b/dev_batteries/pb_cases.json",
    *(f"exploratory/ft1/{module}.py" for module in (
        "__init__", "data", "data_diagnostics", "evaluate_runner", "evaluation",
        "ft1r_data", "kaggle", "memory", "mounts", "plan", "plan_ft1r", "runner",
        "scoring", "selection", "training",
    )),
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False, indent=2) + "\n").encode()


def read_json(path):
    def unique(pairs):
        value = dict(pairs)
        if len(value) != len(pairs):
            raise ValueError("duplicate JSON field")
        return value

    return json.loads(path.read_bytes(), object_pairs_hook=unique)


def git_root(path):
    return ((path / ".git").exists() or (path / ".git").is_symlink()
            or ((path / "HEAD").is_file() and (path / "objects").is_dir()
                and (path / "refs").is_dir()))


def staging_root():
    override = os.environ.get("TRACK_B_STAGING_ROOT")
    if override is not None and not override.strip():
        raise ValueError("TRACK_B_STAGING_ROOT cannot be blank")
    lexical = Path(os.path.abspath(override if override is not None else DEFAULT_ROOT))
    reserved = Path(os.path.abspath("C:/t"))

    def check_ft1(candidate, parent):
        if parent.is_relative_to(candidate) or (
            candidate.is_relative_to(parent)
            and candidate.relative_to(parent).parts[0].lower().startswith("ft1")
        ):
            raise ValueError("Track B staging cannot overlap FT1 staging")

    check_ft1(lexical, reserved)
    path = lexical.resolve()
    check_ft1(path, reserved.resolve())
    for candidate in (lexical, path):
        if ROOT.is_relative_to(candidate) or any(
            git_root(parent) for parent in (candidate, *candidate.parents)
        ):
            raise ValueError("Track B staging cannot overlap a Git repo or worktree")

    try:
        path.stat()
    except FileNotFoundError:
        return path

    def walk_error(error):
        raise error

    for directory, dirs, files in os.walk(path, onerror=walk_error, followlinks=False):
        if ".git" in dirs or ".git" in files or git_root(Path(directory)):
            raise ValueError("Track B staging cannot contain a Git repo or worktree")
        if any((Path(directory) / name).resolve() != Path(directory) / name for name in dirs):
            raise ValueError("Track B staging cannot contain linked directories")
    return path


def binding(commit_sha, adapter_dataset_id, adapter_sha256, model_source, owner):
    if not re.fullmatch("[a-f0-9]{40}", commit_sha) or not re.fullmatch("[a-f0-9]{64}", adapter_sha256):
        raise ValueError("exact commit and adapter hashes required")
    match = re.fullmatch(
        r"[a-z0-9_-]+/ft1-adapter-(2u|2|1)-([1-9][0-9]{0,49})-0449a230200c",
        adapter_dataset_id,
    )
    if not match or not re.fullmatch("[a-z0-9_-]+", owner):
        raise ValueError("expected one eligible-arm FT1 adapter dataset handle and a Kaggle owner")
    core.validate_model_source(model_source, "gemma-3-12b-it")
    arm, seed = match.groups()
    return dict(schema_version=1, stage="B0a", commit_sha=commit_sha,
                ft1_arm=arm, ft1_seed=int(seed), adapter_dataset_id=adapter_dataset_id,
                adapter_sha256=adapter_sha256, model_source=model_source, owner=owner)


def source_at(commit):
    resolved = subprocess.check_output(
        ["git", "rev-parse", "--verify", commit + "^{commit}"], cwd=ROOT, text=True,
    ).strip()
    if resolved != commit:
        raise ValueError("source must name a full commit")
    return subprocess.check_output(
        ["git", "-c", "core.autocrlf=false", "archive", "--format=zip", commit, *SOURCE_PATHS], cwd=ROOT,
    )


def notebook(config, archive, receipt=None):
    # The planned notebook stops before extracting or importing anything.
    config = dict(sorted(config.items()))
    lines = [
        "import base64, hashlib, io, sys, tempfile, zipfile",
        "from pathlib import Path",
        f"CONFIG = {config!r}",
        f"RECEIPT = {receipt!r}",
        "if RECEIPT is None:",
        "    print(CONFIG)",
        "else:",
        f"    archive = base64.b64decode({base64.b64encode(archive).decode()!r})",
        "    if hashlib.sha256(archive).hexdigest() != CONFIG['source_sha256']:",
        "        raise ValueError('source archive hash mismatch')",
        "    with tempfile.TemporaryDirectory() as source:",
        "        zipfile.ZipFile(io.BytesIO(archive)).extractall(source)",
        "        sys.path.insert(0, source)",
        "        from exploratory.track_b.stage_b0a import mounted_run",
        "        mounted_run(CONFIG, RECEIPT, archive)",
    ]
    return dict(nbformat=4, nbformat_minor=5,
                metadata={"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
                cells=[dict(id="b0a", cell_type="code", metadata={}, execution_count=None,
                            outputs=[], source="\n".join(lines) + "\n")])


def bundle(config, archive):
    slug = f"trackb-b0a-{config['ft1_arm']}-{config['ft1_seed']}-{config['commit_sha'][:12]}"
    if len(slug) > 50:
        raise ValueError("Kaggle kernel title exceeds 50 characters")
    metadata = dict(id=f"{config['owner']}/{slug}", title=slug, code_file=NOTEBOOK,
                    language="python", kernel_type="notebook", is_private=True,
                    enable_gpu=True, enable_internet=False,
                    dataset_sources=[config["adapter_dataset_id"], "metaphysika/k2-wheels"],
                    model_sources=[config["model_source"]])
    return {
        BINDING: json_bytes(config),
        METADATA: json_bytes(metadata),
        NOTEBOOK: json_bytes(notebook(config, archive)),
    }


def bundle_hash(files):
    return sha256(json_bytes({name: sha256(raw) for name, raw in files.items()}))


def write_files(folder, files):
    folder.mkdir(parents=True)
    for name, raw in files.items():
        (folder / name).write_bytes(raw)


def stage(name, *, commit_sha, adapter_dataset_id, adapter_sha256, model_source, owner):
    folder = staging_root() / safe_name(name)
    config = binding(commit_sha, adapter_dataset_id, adapter_sha256, model_source, owner)
    archive = source_at(commit_sha)
    config["source_sha256"] = sha256(archive)
    files = bundle(config, archive)
    draft = {key: config[key] for key in RECEIPT_FIELDS & config.keys()}
    draft.update(bundle_sha256=bundle_hash(files), approval_id=None,
                 approval_text=None, created_utc=utc_now())
    write_files(folder, dict(files, **{DRAFT: json_bytes(draft)}))
    return folder


def safe_name(name):
    if not re.fullmatch("[a-z0-9][a-z0-9-]{0,60}", name) or name == "kaggle-owner" or name.startswith("ft1"):
        raise ValueError("expected a Track B staging directory name")
    return name


def validate_receipt(config, receipt, expected_bundle):
    if not isinstance(receipt, dict) or receipt.keys() != RECEIPT_FIELDS:
        raise ValueError("receipt must have exactly the Track B fields")
    if type(receipt["schema_version"]) is not int or any(
        receipt[field] != config[field]
        for field in ("schema_version", "stage", "commit_sha", "adapter_dataset_id", "adapter_sha256")
    ):
        raise ValueError("receipt does not bind this stage, commit and adapter")
    if receipt["bundle_sha256"] != expected_bundle:
        raise ValueError("receipt bundle hash mismatch")
    for key in ("approval_id", "approval_text"):
        if not isinstance(receipt[key], str) or not receipt[key].strip():
            raise ValueError("recorded owner approval required")
    try:
        stamp = datetime.fromisoformat(receipt["created_utc"].replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("receipt creation time must be UTC") from exc
    if stamp.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("receipt creation time must be UTC")


def require_owner(root):
    flag = root / "KAGGLE_OWNER"
    if flag.is_symlink() or not flag.is_file() or flag.read_bytes() != b"trackb":
        raise ValueError("Kaggle owner flag must contain exactly trackb")


def push(name, receipt_path, *, status, backend):
    """Status takes the account owner and supplies a fresh, complete iterable of states."""
    root = staging_root()
    require_owner(root)
    folder = root / safe_name(name)
    if folder.resolve() != folder or any(
        (folder / file).resolve() != folder / file for file in BUNDLE_FILES
    ):
        raise ValueError("staged bundle must use regular Track B paths")
    files = {file: (folder / file).read_bytes() for file in BUNDLE_FILES}
    config = json.loads(files[BINDING])
    verified = binding(**{key: config[key] for key in (
        "commit_sha", "adapter_dataset_id", "adapter_sha256", "model_source", "owner",
    )})
    receipt = read_json(Path(receipt_path))
    validate_receipt(verified, receipt, bundle_hash(files))
    archive = source_at(verified["commit_sha"])
    verified["source_sha256"] = sha256(archive)
    if files != bundle(verified, archive):
        raise ValueError("staged bundle differs from exact Git source")

    lock = root / ".push-lock"
    lock.mkdir()
    try:
        states = status(verified["owner"])
        if isinstance(states, (str, bytes, dict)):
            raise ValueError("status must supply all Kaggle session states")
        states = list(states)
        if any(not isinstance(state, str) or state not in ACTIVE | TERMINAL for state in states):
            raise ValueError("unrecognized Kaggle session state")
        if sum(state in ACTIVE for state in states) >= 2:
            raise ValueError("Kaggle already has two active sessions")
        require_owner(root)
        # Keep the authorized payload, including on an ambiguous push failure.
        # A receipt cannot be used to submit this bundle twice.
        submission = root / ("submitted-" + receipt["bundle_sha256"])
        approved = notebook(verified, archive, receipt)
        write_files(submission, {NOTEBOOK: json_bytes(approved), METADATA: files[METADATA]})
        backend(submission)
    finally:
        lock.rmdir()


def kaggle_push(folder):
    subprocess.run(["kaggle", "kernels", "push", "-p", str(folder),
                    "--accelerator", "NvidiaTeslaT4", "--timeout", str(KAGGLE_TIMEOUT_SECONDS)], check=True)


def command_status(argv, owner):
    """Trust a configured provider to attest that its account query succeeded."""
    value = json.loads(subprocess.check_output(argv, timeout=STATUS_TIMEOUT_SECONDS))
    if (not isinstance(value, dict) or value.get("owner") != owner
            or value.get("account_verified") is not True
            or not isinstance(value.get("states"), list)):
        raise ValueError("status command must attest a successful account query for the staged owner")
    return value["states"]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    for name in ("commit-sha", "adapter-dataset-id", "adapter-sha256", "model-source", "owner"):
        parser.add_argument("--" + name)
    parser.add_argument("--push", action="store_true")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--status-command", nargs=argparse.REMAINDER,
                        help="Last option. Command returning JSON with owner, account_verified and states")
    args = parser.parse_args(argv)
    if args.push:
        if args.receipt is None or not args.status_command:
            parser.error("--push needs --receipt and an account-wide --status-command")

        push(args.name, args.receipt, status=lambda owner: command_status(args.status_command, owner),
             backend=kaggle_push)
    else:
        options = {key: getattr(args, key) for key in (
            "commit_sha", "adapter_dataset_id", "adapter_sha256", "model_source", "owner",
        )}
        if not all(options.values()):
            parser.error("plan needs the exact commit, adapter dataset and hash, model source and owner")
        print(stage(args.name, **options))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
