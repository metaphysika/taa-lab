"""Claude's PR31 overlap sensitivity requirement; no frozen fixture edits."""
from contextlib import contextmanager
import hashlib
import inspect
from pathlib import Path
import textwrap
from unittest.mock import patch

import yaml
from conventional_gateway import backend as conventional, ledger as sql_ledger
from taa_gateway import coverage as native_coverage
from taa_gateway_reference import refunds as reference
from tests.trace_support import production_backend as production, reference_runner
from worlds.refunds.token_bindings import prepare

SOURCE = Path(__file__).parent / 'regression_scenarios/q14_overlap.yaml'
BACKENDS = {'reference': reference, 'production': production, 'conventional': conventional}
MUTATIONS = {
    'reference': (reference, 'claim_coverage', 'if merged and lo<=merged[-1]["to"]:'),
    'production': (native_coverage, 'union', "if merged and left <= merged[-1]['to']:"),
    'conventional': (sql_ledger, 'compute', "if combined and lo<=combined[-1]['to']:"),
}


@contextmanager
def summed_overlap(name):
    module, attribute, branch = MUTATIONS[name]
    original = getattr(module, attribute)
    source = textwrap.dedent(inspect.getsource(original))
    assert source.count(branch) == 1, 'mutation must hit exactly one merge branch'
    changed = source.replace(branch, branch.replace('if ', 'if False and ', 1))
    namespace = dict(original.__globals__)
    exec(compile(changed, '<summed-overlap:' + name + '>', 'exec'), namespace)
    with patch.object(module, attribute, namespace[attribute]):
        yield dict(function=attribute, original_sha256=hashlib.sha256(source.encode()).hexdigest(),
                   mutation_sha256=hashlib.sha256(changed.encode()).hexdigest(),
                   change='Disable interval merging; overlapping lengths sum instead of union.')
    assert getattr(module, attribute) is original


def run(name):
    trace = yaml.safe_load(SOURCE.read_text())[0]
    case = dict(id=trace['id'], trace=trace, parameters={}, source=str(SOURCE))
    program, bindings = prepare(case)
    return reference_runner.run(program, backend=BACKENDS[name], token_bindings=bindings)


def campaign():
    results = {}
    for name in BACKENDS:
        before = run(name)
        assert before and all(row['status'] == 'pass' for row in before), (name, before)
        with summed_overlap(name) as mutation:
            broken = run(name)
        assert not any(row['status'] == 'incomplete' for row in broken), (name, broken)
        failed = [row for row in broken if row['status'] == 'discrepancy' and row['origin'] == 'source']
        assert any(row['assertion'].endswith('.duties') for row in failed), (name, failed)
        assert any(row['assertion'].endswith('.disposition') for row in failed), (name, failed)
        restored = run(name)
        assert restored == before, 'mutation must restore the exact passing observations'
        results[name] = dict(passing=before, summed_overlap=broken, mutation=mutation,
                             source_discrepancies=len(failed), restored_identically=True)
    return results
