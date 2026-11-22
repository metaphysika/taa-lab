"""Execute an approved Test 1 bundle using FT1's base inference and episode loop."""
import json
import os
from pathlib import Path
import time

from exploratory.ft1 import evaluation
from exploratory.ft1.evaluate_runner import prepare
from exploratory.ft1.memory import Tracker
from exploratory.ft1.runner import DeadlineExceeded, deadline

from .analysis import analyze
from .design import KNOWLEDGE_SYSTEM, conditions

MODEL_SOURCE = 'google/gemma-3/transformers/gemma-3-12b-it/1'
SETTINGS = dict(attention='eager', prefill_mode='chunked', prefill_chunk_size=256, prompt_ceiling=14000)
TOTAL_SECONDS = 6 * 60 * 60


def approval_words(config):
    return f"Approve Test 1 {config['phase']} at {config['repo_commit']}"


def validate_approval(config, receipt, practice):
    if (receipt.get('approved') is not True or receipt.get('approval_words') != approval_words(config)
            or receipt.get('binding') != config):
        raise ValueError('separate exact-commit Test 1 approval required')
    if config['settings'] != SETTINGS or config['model_source'] != MODEL_SOURCE:
        raise ValueError('FT1 base settings required')
    if config['phase'] == 'practice':
        return TOTAL_SECONDS
    if (config['phase'] != 'main' or not practice or practice.get('practice_gate_met') is not True
            or practice.get('phase') != 'practice' or practice.get('status') != 'complete'
            or practice.get('repo_commit') != config['repo_commit']
            or not 0 < practice.get('elapsed_seconds', 0) < TOTAL_SECONDS):
        raise ValueError('main requires a passing Test 1 practice report for this commit')
    return TOTAL_SECONDS - practice['elapsed_seconds']


def execute_cell(cell, generate, count_tokens, retain):
    if cell['arm'] == 'knowledge':
        history = [dict(role='user', content=cell['question'])]
        return dict(raw=generate(KNOWLEDGE_SYSTEM, history, 1024, cell['seed']))
    turn = 0

    def call(system, history, cap):
        nonlocal turn
        options = {'assistant_prefill': cell['prefill']} if turn == 0 and cell['prefill'] else {}
        raw = generate(system, history, cap, cell['seed'] + turn, **options)
        turn += 1
        return raw

    row = evaluation.episode(cell['case'], call, count_tokens, retain)
    return dict(packets=row['packets'])


def run(config, receipt, output, practice=None):
    seconds = validate_approval(config, receipt, practice)
    started = time.monotonic()
    check = deadline(seconds)
    output = Path(output)
    output.mkdir(parents=True)

    def append(name, row):
        with (output / name).open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(row, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    rows = []
    status = 'incomplete'
    try:
        generate, count_tokens = prepare(
            '/kaggle/input/models/' + MODEL_SOURCE, None,
            lambda event: append('events.jsonl', event), check, check_decode_deadline=True, **SETTINGS,
        )
        tracker = Tracker(lambda event: append('events.jsonl', event))
        for cell in conditions(config['phase']):
            check()
            identity = dict(arm=cell['arm'], case_id=cell['case_id'])

            def retain(event):
                append('events.jsonl', dict(event, **identity))

            outcome = tracker.call(lambda: execute_cell(cell, generate, count_tokens, retain), None, identity)
            row = dict(identity, **(outcome or {}))
            append('outputs.jsonl', row)
            rows.append(row)
            if tracker.stopped:
                status = 'stopped_mechanical_oom'
                break
        else:
            status = 'complete'
    except DeadlineExceeded:
        status = 'stopped_deadline'
    finally:
        report = analyze(config['phase'], rows)
        report.update(status=status, repo_commit=config['repo_commit'], elapsed_seconds=time.monotonic() - started)
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
