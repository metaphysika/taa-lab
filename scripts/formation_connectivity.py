"""Estimate or run Stage 1's five neutral checks. No study stimuli."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.call_telemetry import BudgetStopped
from formation.checkpoint import TrialStore
from formation.clients import ClaudeChat, GeminiChat, GroqChat, OpenAIChat, ProviderError, ReplyError, list_gemini_models
from formation.credentials import load_keys
from formation.limits import FreeTierLimiter, RatePaused
from formation.telemetry import FormationRecorder

MANIFEST = ROOT / "studies/formation-connectivity-v021.json"


def estimate(manifest, prices):
    rows = []
    for item in manifest["models"]:
        price = prices[item["model"]]
        # Generous 2,000-token input allowance for this tiny neutral prompt.
        rows.append(dict(item, logical_calls=1, request_attempts=1,
                         estimated_full_ceiling_dollars=(2000 * price["input_per_million"] + item["max_output_tokens"] * price["output_per_million"]) / 1000000))
    return {"models": rows, "calls": len(rows), "estimated_full_ceiling_dollars": sum(r["estimated_full_ceiling_dollars"] for r in rows),
            "batch_estimated_stop_dollars": manifest["batch_estimated_stop_dollars"],
            "whole_formation_stop_per_paid_provider": 8,
            "basis": "one attempt per model; full output ceilings, not predicted actual usage; Groq Free account required"}


def fingerprint():
    paths = [MANIFEST, ROOT / "studies/provider-prices-2026-10-07.json", Path(__file__).resolve()]
    paths += sorted((ROOT / "formation").glob("*.py"))
    paths += [ROOT / "agents/call_telemetry.py", ROOT / "agents/gemini_client.py"]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return digest, hashes


def journal_spend(path):
    reserves, charges = {}, {}
    if path.exists():
        for line in path.read_text().splitlines():
            event = json.loads(line)
            if event["event"] == "attempt_start":
                reserves[event["id"]] = event["reserved_dollars"]
            elif event["event"] == "attempt_end" and event.get("estimated_charge_dollars") is not None:
                charges[event["id"]] = event["estimated_charge_dollars"]
    return sum(charges.get(aid, reserve) for aid, reserve in reserves.items())


def run(manifest, prices, output):
    output.mkdir(parents=True, exist_ok=True)
    # This command is sequential; exclude other formation spending commands.
    ledgers = ROOT / "results/formation-spending-v021"
    ledgers.mkdir(parents=True, exist_ok=True)
    lock = ledgers / "run.lock"
    try:
        fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SystemExit("Another run or interrupted lock exists; inspect it before resuming")
    try:
        os.write(fd, str(os.getpid()).encode())
        digest, hashes = fingerprint()
        store = TrialStore(output / "progress.jsonl", digest)
        evidence_path = output / "manifest.json"
        if not evidence_path.exists():
            evidence_path.write_text(json.dumps({"manifest": manifest, "fingerprint": digest, "source_sha256": hashes}, indent=2) + "\n")
        load_keys(ROOT / "keys.env")
        spent_stage = sum(journal_spend(p) for p in output.glob("*-calls.jsonl"))
        for item in manifest["models"]:
            trial, provider = item["model"], item["provider"]
            ledger = ledgers / (provider + ".json")
            prior = json.loads(ledger.read_text())["estimated_api_dollars"] if ledger.exists() else 0
            log = output / (trial.replace("/", "_") + "-calls.jsonl")
            if not store.should_run(trial):
                continue
            cap = min(8, prior + manifest["batch_estimated_stop_dollars"] - spent_stage)
            recorder = FormationRecorder(log, prices, trial, max_logical=2, max_attempts=2,
                                         max_dollars=cap, prior_spend=prior, ledger_path=ledger)
            cls = {"openai": OpenAIChat, "claude": ClaudeChat, "google": GeminiChat, "groq": GroqChat}[provider]
            kwargs = {}
            if provider == "groq":
                kwargs = {"free_tier_confirmed": True, "limiter": FreeTierLimiter(ledgers / "groq-rate.json")}
            client = cls(trial, recorder, max_output_tokens=item["max_output_tokens"], **kwargs)
            store.mark(trial, "inflight")
            try:
                reply = client.chat(manifest["system"], manifest["messages"])
                correct = reply == {"ok": True}
                store.mark(trial, "complete" if correct else "error", reply=reply, matches_expected=correct, accounting=recorder.snapshot())
                print(trial + (": complete" if correct else ": unexpected neutral reply; inspect evidence"))
                if not correct:
                    break
            except RatePaused:
                store.mark(trial, "rate_paused", accounting=recorder.snapshot())
                print(trial + ": rate paused; same command resumes without repeating completed checks")
                break
            except (ProviderError, ReplyError, BudgetStopped) as error:
                store.mark(trial, "error", error=str(error), accounting=recorder.snapshot())
                print(trial + ": stopped: " + str(error))
                break
            spent_stage += recorder.spent - prior
        return all(store.states.get(item["model"]) == "complete" for item in manifest["models"])
    finally:
        os.close(fd)
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--estimate", action="store_true")
    parser.add_argument("--list-gemini-models", action="store_true")
    parser.add_argument("--approved-cost", action="store_true", help="only after Chris's written approval")
    parser.add_argument("--confirm-groq-free-account", action="store_true", help="owner confirms Groq account is Free, with no billing enabled")
    args = parser.parse_args()
    manifest = json.loads(MANIFEST.read_text())
    prices = json.loads((ROOT / manifest["price_file"]).read_text())["models"]
    if args.list_gemini_models:
        load_keys(ROOT / "keys.env")
        models = list_gemini_models()
        out = ROOT / "docs/process/formation-gemini-models-2026-10-07.json"
        if out.exists():
            raise SystemExit("Metadata evidence exists; use a newly dated filename for another listing")
        out.write_text(json.dumps(models, indent=2) + "\n")
        print(json.dumps([m["name"] for m in models], indent=2))
        return
    if args.estimate or not args.approved_cost:
        print(json.dumps(estimate(manifest, prices), indent=2))
        return
    if not args.confirm_groq_free_account:
        raise SystemExit("Confirm your Groq account is Free, without billing, before this batch")
    if not run(manifest, prices, ROOT / manifest["output_dir"]):
        raise SystemExit("Connectivity remains incomplete; inspect progress and evidence")


if __name__ == "__main__":
    main()
