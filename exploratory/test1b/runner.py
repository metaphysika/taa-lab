"""Run a separately approved Test 1b bundle on the mounted FT1 base model."""
import hashlib
import json
import os
from pathlib import Path
import re
import time

from exploratory.ft1 import evaluate_runner, evaluation
from exploratory.ft1.memory import Tracker
from exploratory.ft1.runner import DeadlineExceeded, deadline
from exploratory.test1.runner import MODEL_SOURCE, SETTINGS

from .analysis import analyze
from .design import INSTRUCTIONS, PASS_SEEDS, SAMPLING, TIME_LIMIT_SECONDS, TOKEN_CAP, conditions, identity
from .reply import parse_reply


class InvalidReply(ValueError):
    """A reply failed the format contract before it reached the world."""


def approval_words(config):
    return f"Approve Test 1b {config['phase']} at {config['repo_commit']}"


def run_settings(phase):
    return dict(settings=SETTINGS, sampling=SAMPLING, pass_seeds=list(PASS_SEEDS),
                output_token_cap=TOKEN_CAP, model_source=MODEL_SOURCE,
                time_limit_seconds=TIME_LIMIT_SECONDS[phase])


def validate_approval(config, receipt, trial_bytes):
    phase = config['phase']
    if (phase not in TIME_LIMIT_SECONDS or not re.fullmatch('[0-9a-f]{40}', config['repo_commit'])
            or receipt.get('approved') is not True or receipt.get('approval_words') != approval_words(config)
            or receipt.get('binding') != config):
        raise ValueError('separate exact-commit Test 1b approval required')
    if any(config.get(key) != value for key, value in run_settings(phase).items()):
        raise ValueError('fixed Test 1b run settings required')
    if phase == 'main':
        if trial_bytes is None or hashlib.sha256(trial_bytes).hexdigest() != receipt.get('trial_report_sha256'):
            raise ValueError('main approval must bind the passing same-commit trial report bytes')
        trial = json.loads(trial_bytes)
        elapsed = trial.get('elapsed_seconds')
        versions = trial.get('versions', {})
        if (trial.get('trial_gate_met') is not True or trial.get('complete_roster') is not True
                or trial.get('passes_differ') is not True or trial.get('identical_pass_pairs') != []
                or trial.get('phase') != 'trial' or trial.get('status') != 'complete'
                or trial.get('repo_commit') != config['repo_commit']
                or type(elapsed) not in (int, float) or not 0 < elapsed <= TIME_LIMIT_SECONDS['trial']
                or set(versions) != set(INSTRUCTIONS)
                or any(v.get('planned') != 8 or v.get('format_valid') != 8 for v in versions.values())):
            raise ValueError('main requires a passing Test 1b trial report from this commit')
    return TIME_LIMIT_SECONDS[phase]


def prepare(retain, check):
    model, tokenizer, _ = evaluate_runner.load_base('/kaggle/input/models/' + MODEL_SOURCE,
                                                     retain, check, attention=SETTINGS['attention'])
    evaluate_runner.attention_readback(model, SETTINGS['attention'], retain, 'base')
    core = evaluate_runner.core
    end = core.end_token(tokenizer, 'gemma-3-12b-it')
    marker = '<start_of_turn>'
    turn_start = tokenizer.convert_tokens_to_ids(marker)
    if (type(turn_start) is not int or turn_start == getattr(tokenizer, 'unk_token_id', None)
            or tokenizer.convert_ids_to_tokens(turn_start) != marker
            or tokenizer.encode(marker, add_special_tokens=False) != [turn_start]):
        raise ValueError('Gemma start-of-turn marker must be atomic')
    eos = tokenizer.eos_token_id
    extra_stops = (turn_start,) if eos is None or eos == end else (turn_start, eos)
    generate, count_tokens = evaluate_runner.generation_functions(
        model, tokenizer, check, prompt_ceiling=SETTINGS['prompt_ceiling'],
        prefill_mode=SETTINGS['prefill_mode'], prefill_chunk_size=SETTINGS['prefill_chunk_size'],
        check_decode_deadline=True, sampling=SAMPLING, extra_stop_ids=extra_stops,
    )

    def decoded(system, history, seed):
        ids = generate(system, history, TOKEN_CAP, seed, return_ids=True)
        decoded.last_output_tokens = len(ids)
        if ids and ids[-1] in (end, eos):
            ids = ids[:-1]
        # Preserve unexpected markers, including the start token that stopped decoding.
        return tokenizer.decode(ids, skip_special_tokens=False, clean_up_tokenization_spaces=False)

    return decoded, count_tokens


def execute_cell(cell, generate, count_tokens, retain, replies):
    def call(system, history, _cap):
        turn = len(replies)
        # FT1 rebuilds history from the base case. Preserve the instruction in the original user turn.
        history[0]['content'] += '\n\n' + cell['instruction']
        system = system.replace('Return one JSON object per turn:',
                                'After the first turn, return one JSON object per turn. Use this action format:')
        raw = generate(system, history, cell['seed'] + turn)
        replies.append(raw)
        try:
            parse_reply(raw, first=turn == 0)
        except ValueError as exc:
            retain(dict(event='invalid_reply', turn=turn, raw=raw, reason=str(exc)))
            raise InvalidReply from exc
        return raw

    def log_turn(event):
        tokens = getattr(generate, 'last_output_tokens', event['reply_tokens'])
        retain(dict(event, generated_tokens=tokens, cap_hit=tokens >= TOKEN_CAP))

    try:
        evaluation.episode(cell['case'], call, count_tokens, log_turn)
    except InvalidReply:
        return None


def run(config, receipt, output, trial_bytes=None):
    seconds = validate_approval(config, receipt, trial_bytes)
    started = time.monotonic()
    check = deadline(seconds)
    output = Path(output)
    output.mkdir(parents=True)

    def append(name, row):
        with (output / name).open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    phase = config['phase']
    rows = []
    status = 'incomplete'
    try:
        generate, count_tokens = prepare(lambda event: append('events.jsonl', event), check)
        tracker = Tracker(lambda event: append('events.jsonl', event))
        for cell in conditions(phase):
            check()
            cell_id = identity(cell)
            replies = []

            def retain(event):
                append('events.jsonl', dict(event, **cell_id))

            try:
                tracker.call(lambda: execute_cell(cell, generate, count_tokens, retain, replies), None, cell_id)
            finally:
                row = dict(cell_id, replies=replies)
                append('outputs.jsonl', row)
                rows.append(row)
            check()
            if tracker.stopped:
                status = 'stopped_mechanical_oom'
                break
        else:
            status = 'complete'
    except DeadlineExceeded:
        status = 'stopped_deadline'
    finally:
        report = analyze(phase, rows)
        report.update(status=status, repo_commit=config['repo_commit'], elapsed_seconds=time.monotonic() - started)
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
