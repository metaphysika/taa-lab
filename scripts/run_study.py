"""Versioned follow-up runner. Dry-run performs no provider request.

Examples (after the notebook's paid-batch authorization):
  python3 scripts/run_study.py --manifest studies/obligations-free.json
  python3 scripts/run_study.py --manifest studies/obligations-luna-smoke.json --dry-run
  python3 scripts/run_study.py --manifest studies/obligations-luna-smoke.json --provider openai
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

STUDY_SOURCES = (
    "run.py", "taa/gate.py", "taa/study_gate.py", "taa/obligations.py",
    "taa/counsel.py", "taa/premises.py", "taa/preview.py", "taa/records.py",
    "world/fake_world.py", "agents/obedient_agent.py", "agents/scripted_agent.py",
    "agents/timeline_agent.py", "agents/openai_client.py",
    "agents/anthropic_client.py", "agents/call_telemetry.py",
    "evaluation/outcomes.py", "scripts/run_study.py")

from agents.call_telemetry import BudgetStopped, CallRecorder
from agents.timeline_agent import TimelineAgent
from evaluation.outcomes import score_obligations
from taa.study_gate import MODES, StudyGate, StudyModel


class FixtureReviewer:
    """Always approves. A structural test fixture, never model or human evidence."""
    model = "deterministic-all-approve-fixture"

    def json(self, prompt):
        return {"verdict": "approve", "reason": "deterministic fixture approval",
                "approved_targets": "all", "premises": []}


class MoralRefusalFixture:
    """Free F09 mechanism check with a declared refusal, not reviewer evidence."""
    model = "deterministic-moral-refusal-fixture"

    def __init__(self):
        self.reviewed_wrongful_instruction = False

    def json(self, prompt):
        requested_p = ("The act requested now is on P" in prompt or
                       ('"shipment_id": "P"' in prompt and "Requested act:" in prompt))
        if requested_p:
            evidence = ("free the seat for premium client P", '"source_id": "Dispatch Authority"',
                        '"authenticated": true', "time-critical medical supplies")
            if not all(fact in prompt for fact in evidence):
                raise ValueError("F09 moral fixture did not receive the declared current evidence")
            self.reviewed_wrongful_instruction = True
            return {"verdict": "stop" if "The act requested now is on P" in prompt else "refuse",
                    "grave": True, "reason":
                    "P would consume the seat freed by withdrawing still-needed U"}
        if "Original stop reason:" in prompt:
            return {"approved_targets": []}
        return {"verdict": "approve", "approved_targets": "all", "grave": False,
                "premises": [], "reason": "fixture approval"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    return {name: digest(ROOT / name) for name in STUDY_SOURCES}


def load_manifest(path):
    with open(path) as source:
        m = json.load(source)
    if m.get("schema") != "obligations-study-v1":
        raise ValueError("wrong study manifest schema")
    if m["stage"] not in ("free", "free_regression", "smoke", "pilot", "final", "regression"):
        raise ValueError("unknown stage")
    if not m.get("cases") or not m.get("modes") or not isinstance(m.get("repeats"), int):
        raise ValueError("cases, modes, and integer repeats are required")
    if m["repeats"] < 1 or any(mode not in MODES for mode in m["modes"]):
        raise ValueError("bad repeat count or gate mode")
    if m.get("fixture_reviewer") not in (None, "all_approve", "moral_refusal"):
        raise ValueError("unknown fixture reviewer")
    if m.get("fixture_reviewer") and m["stage"] not in ("free", "free_regression"):
        raise ValueError("paid stage cannot select a deterministic fixture reviewer")
    if len(set(m["modes"])) != len(m["modes"]):
        raise ValueError("duplicate modes")
    if m["stage"] not in ("free", "free_regression"):
        b = m.get("budget", {})
        for key in ("max_logical_calls", "max_request_attempts", "stage_max_dollars", "global_max_dollars"):
            if not isinstance(b.get(key), (int, float)) or b[key] <= 0:
                raise ValueError(f"missing positive budget field {key}")
        if not m.get("models") or not m.get("price_file") or not m.get("spending_ledger"):
            raise ValueError("paid manifest requires pinned models, price file, and spending ledger")
        price_path = ROOT / m["price_file"]
        if not price_path.is_file():
            raise ValueError("paid manifest price file is missing")
        configured = json.loads(price_path.read_text())["models"]
        if any(model not in configured for model in m["models"].values()):
            raise ValueError("price file lacks a pinned model")
    for case in m["cases"]:
        if not case.startswith("scenarios/"):
            raise ValueError("case must have an explicit scenario path")
        if m["stage"] in ("regression", "free_regression"):
            if case.startswith("scenarios/followup/") or m.get("agents", {}).get(case) not in (
                    "obedient", "scripted"):
                raise ValueError("regression cases need explicit legacy agent kinds")
        elif not case.startswith("scenarios/followup/"):
            raise ValueError("core cases must have explicit follow-up paths")
        scenario_path = ROOT / case
        if not scenario_path.is_file():
            raise ValueError(f"missing case {case}")
        if m.get("scenario_hashes") and m["scenario_hashes"].get(case) != digest(scenario_path):
            raise ValueError(f"scenario hash mismatch: {case}")
        with scenario_path.open() as source:
            scenario = json.load(source)
        if m["stage"] not in ("regression", "free_regression") and scenario.get(
                "study", {}).get("version") != "obligations-v1":
            raise ValueError(f"wrong scenario version: {case}")
    return m


def episode_order(manifest):
    for case in manifest["cases"]:
        for repeat in range(1, manifest["repeats"] + 1):
            modes = manifest["modes"]
            rotation = (repeat - 1) % len(modes)
            for mode in modes[rotation:] + modes[:rotation]:
                yield case, repeat, mode


def run_episode(scenario, mode, inner_model, recorder=None, checkpoint=None,
                agent_kind="timeline"):
    # Importing run here lets the harness load keys.env in its normal way. The script
    # itself never inspects or prints credentials. Dry-run never reaches this import.
    from run import build, missed_work, score
    world, warrant, registry = build(scenario)
    if agent_kind == "timeline":
        agent = TimelineAgent(scenario)
        candidates = agent.candidates
    elif agent_kind == "obedient":
        from agents.obedient_agent import ObedientAgent
        agent = ObedientAgent(scenario)
        candidates = [s["id"] for s in world.shipments]
    elif agent_kind == "scripted":
        from agents.scripted_agent import ScriptedAgent
        agent = ScriptedAgent(scenario)
        candidates = [s["id"] for s in world.shipments]
    else:
        raise ValueError(f"unknown scripted agent: {agent_kind}")
    agent.warrant = warrant
    model = (StudyModel(inner_model, world, candidates, recorder=recorder)
             if mode != "expiring_obligations" else None)
    api_before = recorder.snapshot() if recorder else None
    gate = StudyGate(mode, world, warrant, registry, model)
    reasons = []
    def save_checkpoint():
        if checkpoint:
            checkpoint({"status": "incomplete", "step": world.step, "mode": mode,
                        "gate_log": gate.log, "referrals": gate.referrals,
                        "agent_reasons": reasons, "effects": world.effects,
                        "authority_directives": world.authority_directives,
                        "independent_authority_notices": world.study_notices,
                        "claims_current": world.claims, "ledger": gate.ledger.snapshot(),
                        "step_history": gate.step_history,
                        "execution_checks": gate.execution_checks,
                        "reviewer_calls": model.calls if model else 0,
                        "api": recorder.snapshot() if recorder else None})
    save_checkpoint()
    if mode.startswith("taa_"):
        reviewed = gate.submit_plan(agent.propose_plan(warrant, world.observe()))
        if reviewed.status == "stopped":
            gate.submit_plan(agent.revise_plan(warrant, world.observe(), "; ".join(reviewed.review_notes)))
        save_checkpoint()
    feedback = None
    for _ in range(scenario["steps"]):
        world.advance()
        gate.after_advance()
        tool, args, reason = agent.decide(world.observe(), feedback)
        reasons.append({"step": world.step, "tool": tool, "args": args, "reason": reason})
        feedback = gate.request(tool, args) if tool else None
        gate.end_step()
        save_checkpoint()
    failure_events = model.failures if model else []
    legacy_score = score(world)
    legacy_missed = missed_work(world, scenario)
    if scenario.get("study", {}).get("version") == "obligations-v1":
        outcome = score_obligations(scenario, world, gate, gate.ledger, gate.step_history,
                                    gate.execution_checks, failure_events)
    else:
        outcome = {"evaluation_version": "legacy-regression-v1",
                   "grave": legacy_score["grave"], "questionable": legacy_score["questionable"],
                   "unauthorized": legacy_score["unauthorized"], "undone": legacy_missed,
                   "simulated_shipping_cost": legacy_score["cost"],
                   "api_or_format_failures": failure_events}
    api_after = recorder.snapshot() if recorder else None
    api_delta = ({key: round(api_after[key] - api_before[key], 8)
                  for key in ("logical_calls", "request_attempts", "input_tokens", "output_tokens",
                              "cached_input_tokens", "cache_write_tokens", "estimated_api_dollars")}
                 if recorder else {"estimated_api_dollars": 0})
    return {"status": "complete", "mode": mode, "outcome": outcome,
            "legacy_score": legacy_score, "legacy_missed_work": legacy_missed,
            "gate_log": gate.log, "referrals": gate.referrals,
            "agent_reasons": reasons, "effects": world.effects,
            "authority_directives": world.authority_directives,
            "independent_authority_notices": world.study_notices,
            "claims_final": world.claims, "ledger": gate.ledger.snapshot(),
            "step_history": gate.step_history, "execution_checks": gate.execution_checks,
            "reports_to_human": world.reports, "reviewer_calls": model.calls if model else 0,
            "api": api_delta}


def paid_model(provider, model_id, recorder):
    if provider == "openai":
        from agents.openai_client import OpenAI
        client = OpenAI(model=model_id, recorder=recorder)
    elif provider == "claude":
        from agents.anthropic_client import Claude
        client = Claude(model=model_id, recorder=recorder)
    else:
        raise ValueError("provider must be openai or claude")
    if model_id not in client.list_models():
        raise RuntimeError(f"pinned model {model_id} is unavailable; no substitution made")
    return client


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--provider", choices=("openai", "claude"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    manifest_path = ROOT / args.manifest
    m = load_manifest(manifest_path)
    manifest_hash = digest(manifest_path)
    code_hashes = source_hashes()
    price_hash = digest(ROOT / m["price_file"]) if m.get("price_file") else None
    free_stage = m["stage"] in ("free", "free_regression")
    provider = args.provider or ("fixture" if free_stage else None)
    if provider is None or (free_stage and provider != "fixture"):
        parser.error("paid stages require --provider; free stage uses the fixture")
    if provider != "fixture" and provider not in m["models"]:
        parser.error("manifest has no pinned model for that provider")
    episodes = list(episode_order(m))
    print(json.dumps({"stage": m["stage"], "provider": provider,
                      "model": m.get("models", {}).get(provider),
                      "manifest_sha256": manifest_hash, "episodes": len(episodes),
                      "modes": m["modes"], "repeats": m["repeats"],
                      "budget": m.get("budget")}, indent=2))
    if args.dry_run:
        return 0

    out_dir = ROOT / m["output_dir"] / provider
    metadata_path = out_dir / "manifest-record.json"
    ledger_path = ROOT / m["spending_ledger"] if provider != "fixture" else None
    prior = (json.loads(ledger_path.read_text())["estimated_api_dollars"]
             if ledger_path and ledger_path.exists() else 0.0)
    stage_start = prior
    if provider != "fixture":
        stage_budget_path = ROOT / m["output_dir"] / "stage-budget.json"
        if stage_budget_path.exists():
            saved_budget = json.loads(stage_budget_path.read_text())
            if saved_budget["manifest_sha256"] != manifest_hash:
                raise SystemExit("stage budget belongs to a different manifest")
            if (saved_budget.get("source_hashes") != code_hashes or
                    saved_budget.get("price_sha256") != price_hash):
                raise SystemExit("code or prices changed within a paid stage")
            stage_start = saved_budget["start_estimated_api_dollars"]
        elif not args.resume:
            stage_budget_path.parent.mkdir(parents=True, exist_ok=True)
            stage_budget_path.write_text(json.dumps({"manifest_sha256": manifest_hash,
                "source_hashes": code_hashes, "price_sha256": price_hash,
                "start_estimated_api_dollars": prior}, indent=2) + "\n")
    if out_dir.exists() and not args.resume:
        raise SystemExit(f"output exists; use --resume for missing episodes only: {out_dir}")
    if args.resume:
        if not metadata_path.exists():
            raise SystemExit("cannot resume without an identical saved manifest record")
        saved = json.loads(metadata_path.read_text())
        if saved["manifest_sha256"] != manifest_hash:
            raise SystemExit("manifest changed; refusing to mix versions")
        if saved.get("source_hashes") != code_hashes or saved.get("price_sha256") != price_hash:
            raise SystemExit("code or prices changed; refusing to resume an old version")
    else:
        out_dir.mkdir(parents=True)
        metadata_path.write_text(json.dumps({"manifest_sha256": manifest_hash, "manifest": m,
                                             "provider": provider,
                                             "source_hashes": code_hashes,
                                             "price_sha256": price_hash,
                                             "stage_start_estimated_api_dollars": stage_start}, indent=2) + "\n")

    recorder = None
    client = (MoralRefusalFixture() if m.get("fixture_reviewer") == "moral_refusal"
              else FixtureReviewer())
    if provider != "fixture":
        price_config = json.loads((ROOT / m["price_file"]).read_text())
        model_id = m["models"][provider]
        if model_id not in price_config["models"]:
            raise SystemExit("missing exact pinned model price")
        stage_start = json.loads(metadata_path.read_text())["stage_start_estimated_api_dollars"]
        limit = min(m["budget"]["global_max_dollars"],
                    stage_start + m["budget"]["stage_max_dollars"])
        recorder = CallRecorder(out_dir / "calls.jsonl", price_config["models"], model_id,
                                m["budget"]["max_logical_calls"], m["budget"]["max_request_attempts"],
                                limit, prior_spend=prior, ledger_path=ledger_path)
        client = paid_model(provider, model_id, recorder)

    for case, repeat, mode in episodes:
        episode_id = f"{Path(case).stem}-{mode}-r{repeat:02d}"
        path = out_dir / f"{episode_id}.json"
        partial_path = out_dir / f"{episode_id}.partial.json"
        if path.exists():
            existing = json.loads(path.read_text())
            if existing.get("status") == "complete":
                continue
            raise SystemExit(f"incomplete episode retained for inspection: {path}")
        if recorder:
            recorder.context = {"stage": m["stage"], "case": case, "repeat": repeat, "mode": mode}
        with (ROOT / case).open() as source:
            scenario = json.load(source)
        try:
            episode = run_episode(scenario, mode, client, recorder,
                                  checkpoint=lambda state: partial_path.write_text(
                                      json.dumps(state, indent=2) + "\n"),
                                  agent_kind=m.get("agents", {}).get(case, "timeline"))
        except Exception as exc:
            episode = {"status": "incomplete", "error_type": type(exc).__name__,
                       "error": str(exc), "api": recorder.snapshot() if recorder else None,
                       "checkpoint": str(partial_path)}
            path.write_text(json.dumps(episode, indent=2) + "\n")
            print(f"INCOMPLETE {episode_id}: {exc}", file=sys.stderr)
            raise
        episode.update({"case": case, "repeat": repeat, "provider": provider,
                        "model": m.get("models", {}).get(provider, client.model),
                        "manifest_sha256": manifest_hash})
        path.write_text(json.dumps(episode, indent=2) + "\n")
        partial_path.unlink(missing_ok=True)
        outcome = episode["outcome"]
        lost = outcome.get("avoidable_ordinary_work_lost", outcome.get("undone", 0))
        print(f"complete {episode_id}: unmet={outcome.get('serious_unmet_need_ids', [])} "
              f"lost={lost} calls={episode['reviewer_calls']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
