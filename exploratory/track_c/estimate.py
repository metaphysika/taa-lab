"""Offline estimates based on the built request bodies and assumed history growth."""
import json
from math import ceil

from .protocol import MODELS, PROBE, REPEATS, SYSTEM, TOOLS, load_cases, request
from .transport import RATES


def tokens(value):
    # Planning approximation of four serialized characters per token.
    return ceil(len(json.dumps(value, ensure_ascii=False)) / 4)


def main():
    cases, reply = load_cases()
    print(f"System: {len(SYSTEM)} characters; tools: {len(json.dumps(TOOLS))} serialized characters")
    sizes = [len(case["prompt"]) for case in cases]
    print(f"Case prompts: {min(sizes)}–{max(sizes)} characters across {len(cases)} cases")
    for model, assumed_output in zip(MODELS, (2000, 4000)):
        episode_input = probe_input = 0
        for case in cases:
            messages = [{"role": "user", "content": case["prompt"]}]
            for turn in range(4):
                episode_input += REPEATS * tokens(request(model, messages))
                # Allow signature/framing and rebill all assumed prior output at
                # full input price, covering restored thinking in tool loops.
                episode_input += REPEATS * (100 + assumed_output // 4) * turn
                messages.extend([
                    {"role": "assistant", "content": [{"type": "tool_use", "name": "run_check",
                                                      "id": f"toolu_example_{turn}", "input": {}}]},
                    {"role": "user", "content": [{"type": "tool_result", "tool_use_id": f"toolu_example_{turn}",
                                                 "content": max(reply, case["check_result"], key=len)}]},
                ])
            prompt = [{"role": "user", "content": case["prompt"] + "\n\n" + PROBE}]
            probe_input += tokens(request(model, prompt, probe=True))
        total_input = episode_input + probe_input
        total_output = assumed_output * len(cases) * REPEATS + 256 * len(cases)
        input_rate, output_rate = RATES[model]
        point = (total_input * input_rate + total_output * output_rate) / 10_000_000
        print(f"{model}: {total_input:,} input / {total_output:,} output tokens, "
              f"point ${point:.4f}, buffered ${point * 1.5:.4f}")


if __name__ == "__main__":
    main()
