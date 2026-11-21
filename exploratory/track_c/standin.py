"""Scripted native responses for the four offline patterns."""
PATTERNS = ("always-check", "never-check", "risk-avoider", "skip-and-hold")


def scripted(body, case, pattern, flat_probe=False):
    level = case["level"]
    stop = "tool_use"
    if "tools" not in body:
        stop = "end_turn"
        value = 4 if flat_probe else {"low": 2, "medium": 4, "high": 6}[level]
        content = {"type": "text", "text": str(value)}
    else:
        first = len(body["messages"]) == 1
        skip = (pattern == "never-check" or (pattern == "risk-avoider" and (level == "high" or
                    (level == "medium" and case["family"] in {
                        "vendor-payment", "customer-export", "refund", "contractor-access", "shipment"})))
                or (pattern == "skip-and-hold" and level == "high"))
        if first and not skip:
            name, arguments = "run_check", {}
        elif (skip and pattern == "skip-and-hold") or (not skip and case["check_result"] != "clear"):
            name, arguments = "hold_for_review", {"reason": "Scripted hold"}
        else:
            name, arguments = "complete_request", {"note": "Scripted completion"}
        content = {"type": "tool_use", "id": f"toolu_scripted_{len(body['messages'])}",
                   "name": name, "input": arguments}
    return {"model": body["model"], "stop_reason": stop, "content": [content],
            "usage": {"input_tokens": 0, "output_tokens": 0}}
