"""Fixed limits the gate enforces itself, before any review (v0.13).

A cap such as "at most $300 in total to one customer" is a determinate rule (in Aquinas's terms, a
determinatio of human law). Applying it needs arithmetic, not judgment, so no reviewer is asked to
apply it and no review can widen it.

Every gate checks caps, plain permissions included. A spending cap is ordinary permission
engineering, like the tool budget plain permissions already enforce; giving it only to the
purpose-checking gates would credit TAA with what simple restrictions do.
"""
import inspect

from taa.records import target_of


def caps_for(scenario):
    """The warrant's caps, as {tool: {"total_amount_per_target": dollars}}.

    A scenario can state caps in its warrant (`"caps"`). No scenario does yet, so the one cap the
    scenarios already record is read as well: `credit_cap_per_customer`, which `split_credits`
    states in words in the warrant's purpose ("up to $300 per customer"), which the world enforces
    per single credit, and which the scorer uses for the grave count. It is read here as the
    warrant's cap on the total credited to one customer."""
    warrant = scenario["warrant"]
    caps = {tool: dict(rule) for tool, rule in warrant.get("caps", {}).items()}
    recorded = scenario["world"].get("credit_cap_per_customer")
    if recorded is not None and "issue_credit" in warrant["allowed_tools"]:
        caps.setdefault("issue_credit", {"total_amount_per_target": int(recorded)})
    return caps


def default_amount(tool_function):
    """The amount a tool uses when the agent names none (e.g. issue_credit's $300 default)."""
    try:
        default = inspect.signature(tool_function).parameters["amount"].default
    except (KeyError, TypeError, ValueError):
        return None
    return None if default is inspect.Parameter.empty else default


def amount_of(args, default):
    """The whole-dollar amount of an act, or None if it has none or it can't be read (the world
    then rejects the act itself)."""
    value = args.get("amount", default) if isinstance(args, dict) else default
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def cap_refusal(caps, tool, args, log, default):
    """Why this act would take its target past a cap, or None if it stays within every cap.
    Counts the money this gate has already let through to the same target with the same tool."""
    cap = caps.get(tool, {}).get("total_amount_per_target")
    target = target_of(args)
    amount = amount_of(args, default)
    if cap is None or target is None or amount is None:
        return None
    given = sum(amount_of(e["args"], default) or 0 for e in log
                if e["tool"] == tool and e["decision"] == "ALLOWED" and e.get("spent")
                and target_of(e["args"]) == target)
    if given + amount <= cap:
        return None
    return (f"fixed limit: the warrant allows at most ${cap} in total per target for {tool} "
            f"(${given} given to {target} already); no review can widen it")
