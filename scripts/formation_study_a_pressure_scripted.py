"""Free pressure-variant verification only; never loads credentials or providers."""
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from formation.study_a import load_cases
from formation.study_a_pressure import replay_pressure
from scripts.formation_study_a_scripted import run_fixtures

MANIFEST = ROOT / 'studies/formation-study-a-pressure-scripted-v0215.json'


def run_pressure_fixtures(manifest_path=MANIFEST, output=None):
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text())
    cases = {c['id']: c for c in load_cases([ROOT/p for p in manifest['scenario_paths']])}
    if not all(c.get('variant_version') == 'v0.21.5' and 'issuer_followup' in c for c in cases.values()):
        raise ValueError('pressure-only draft manifest required')
    summary = run_fixtures(manifest_path, output)
    output = Path(output) if output is not None else ROOT / manifest['output_dir']
    fixtures = json.loads((ROOT / manifest['fixture_file']).read_text())['fixtures']
    for fixture in fixtures:
        path = output / (fixture['case_id'] + '-' + fixture['name'] + '.json')
        original = json.loads(path.read_text())
        pressure = replay_pressure(cases[fixture['case_id']], fixture['packets'])
        if pressure['score'] != original['score']:
            raise AssertionError('pressure changed the approved scoring behavior')
        original['issuer_message_deliveries'] = pressure['issuer_message_deliveries']
        path.write_text(json.dumps(original,indent=2)+'\n')
    evidence_path = output / 'manifest.json'
    evidence = json.loads(evidence_path.read_text())
    for relative in ('formation/study_a_pressure.py','scripts/formation_study_a_pressure_scripted.py'):
        evidence['source_sha256'][relative] = hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()
    evidence['stage'] = 'Free pressure draft fixtures; not a study freeze or model observation'
    evidence_path.write_text(json.dumps(evidence,indent=2)+'\n')
    (output/'summary.md').write_text((output/'summary.md').read_text().replace('Study A Stage 2 free verification','Study A pressure draft free verification'))
    return summary

if __name__ == '__main__':
    summary = run_pressure_fixtures()
    print('%d/%d declared fixtures pass; 0 model calls; $0' % (summary['passed'],summary['fixture_count']))
    if summary['passed'] != summary['fixture_count']:
        raise SystemExit('pressure draft verification failed')
