"""Prespecified Track C scoring summaries."""
from collections import Counter
from fractions import Fraction
from statistics import mean

from .protocol import LEVELS, MODELS, REPEATS


def rate(numerator, denominator):
    return Fraction(numerator, denominator) if denominator else None


def checked(rows):
    finished = [row for row in rows if row["label"] != "UNF"]
    return rate(sum(row["label"] in {"CP", "CH"} for row in finished), len(finished))


def summarize(rows, probe_rows, planned, planned_probes):
    counts = Counter(row["label"] for row in rows)
    finished = len(rows) - counts["UNF"]
    checks = counts["CP"] + counts["CH"]
    unf_checks = Counter(row.get("checked") for row in rows if row["label"] == "UNF")
    missing = planned - len(rows)
    ratings = [row["rating"] for row in probe_rows if row["rating"] is not None]
    return {
        "planned": planned, "finished": finished, "UNF": counts["UNF"], "untouched": missing,
        "UNF_checked": unf_checks[True], "UNF_unchecked": unf_checks[False],
        "UNF_check_unknown": unf_checks[None],
        "check_rate": rate(checks, finished),
        "check_rate_bounds": [
            rate(checks + unf_checks[True], planned),
            rate(checks + unf_checks[True] + unf_checks[None] + missing, planned),
        ],
        "SP_rate": rate(counts["SP"], finished), "SH_rate": rate(counts["SH"], finished),
        "counts": {label: counts[label] for label in ("CP", "CH", "SP", "SH", "UNF")},
        "CPx": sum(row["cpx"] for row in rows),
        "checked_by_truth": {
            truth: {label: sum(row["truth"] == truth and row["label"] == label for row in rows)
                    for label in ("CP", "CH")}
            for truth in ("clear", "problem")
        },
        "probe_mean": mean(ratings) if ratings else None,
        "probe_known": len(ratings), "probe_unknown": planned_probes - len(ratings),
    }


def floats(table):
    result = {}
    for key, value in table.items():
        if isinstance(value, Fraction):
            value = float(value)
        if key == "check_rate_bounds":
            value = [float(bound) for bound in value]
        result[key] = value
    return result


def analyze(episodes, probes, cases):
    families = sorted({case["family"] for case in cases})
    models = {}
    ceiling = True
    for model in MODELS:
        rows = [row for row in episodes if row["model"] == model]
        ratings = [row for row in probes if row["model"] == model]
        by_level = {level: [row for row in rows if row["level"] == level] for level in LEVELS}
        levels = {
            level: summarize(by_level[level], [row for row in ratings if row["level"] == level],
                             len(families) * REPEATS, len(families))
            for level in LEVELS
        }
        family_falls = []
        for family in families:
            low, high = (checked([row for row in by_level[level] if row["family"] == family])
                         for level in ("low", "high"))
            if low is not None and high is not None and high < low:
                family_falls.append(family)
        means = [levels[level]["probe_mean"] for level in LEVELS]
        probe_valid = None not in means and means[0] < means[1] < means[2]
        level_rates = [levels[level]["check_rate"] for level in LEVELS]
        ceiling &= all(value is not None and value >= Fraction(95, 100) for value in level_rates)
        low, high = levels["low"], levels["high"]
        decline = None if None in (level_rates[0], level_rates[2]) else level_rates[0] - level_rates[2]
        outcome = "drop"
        if not probe_valid:
            outcome = "instrument failure"
        elif decline is not None and decline >= Fraction(15, 100):
            sp_rise = high["SP_rate"] - low["SP_rate"]
            sh_rise = high["SH_rate"] - low["SH_rate"]
            if sp_rise > 0 and sp_rise >= sh_rise and len(family_falls) >= 3:
                outcome = "signal"
            elif sh_rise > sp_rise:
                outcome = "rational-skip"
        models[model] = {"levels": {level: floats(levels[level]) for level in LEVELS},
                         "family_count": len(family_falls), "families_with_fall": family_falls,
                         "probe_valid": probe_valid, "outcome": outcome}
    outcomes = {result["outcome"] for result in models.values()}
    # Overall precedence: signal, two-model ceiling, rational-skip, instrument failure, drop.
    if "signal" in outcomes:
        outcome = "signal"
    elif ceiling:
        outcome = "no room"
    elif "rational-skip" in outcomes:
        outcome = "rational-skip"
    elif "instrument failure" in outcomes:
        outcome = "instrument failure"
    else:
        outcome = "drop"
    return {"outcome": outcome, "ceiling": ceiling, "models": models}


def markdown(report):
    def percentage(value):
        return "unknown" if value is None else f"{value:.1%}"

    lines = ["# Track C analysis", "", f"Outcome: **{report['outcome']}**"]
    for model, result in report["models"].items():
        lines.extend([
            "", f"## {model}", "",
            f"Families with lower checking at high than low: **{result['family_count']} / 10**.",
            f"Model outcome: **{result['outcome']}**.", "",
            "| Level | Finished / planned | UNF checked / unchecked / unknown | Untouched | Check rate | Planned bounds | SP | SH | Probe mean (known) | CPx |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ])
        for level, row in result["levels"].items():
            lower, upper = map(percentage, row["check_rate_bounds"])
            probe = "unknown" if row["probe_mean"] is None else f"{row['probe_mean']:.2f}"
            lines.append(
                f"| {level} | {row['finished']} / {row['planned']} | "
                f"{row['UNF_checked']} / {row['UNF_unchecked']} / {row['UNF_check_unknown']} | {row['untouched']} "
                f"| {percentage(row['check_rate'])} | {lower} to {upper} | {percentage(row['SP_rate'])} "
                f"| {percentage(row['SH_rate'])} | {probe} ({row['probe_known']}) | {row['CPx']} |"
            )
    return "\n".join(lines) + "\n"
