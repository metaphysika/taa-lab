"""No-credential offline entrypoint; live dispatch is separately gated."""
import argparse
import json

from experiment_b.audit import summarize
from experiment_b.fixtures import verify
from experiment_b.native import Native
from experiment_b.runner import Evidence, run
from experiment_b.standin import ScriptedWire


def offline(directory, mode='key_following'):
    pins = verify()
    evidence = Evidence(directory)
    try:
        evidence.retain('manifest', dict(mode='OFFLINE_SYNTHETIC', standin=mode, pins=pins,
                                         model_calls=0, spend='0', scientific_headroom=False))

        def factory(identity, host, log):
            provider = 'responses' if identity['model'] == 'Luna' else 'anthropic'
            model = 'offline-' + identity['model']
            return Native(provider, model, {}, ScriptedWire(host, provider, model, mode), log)

        rows = run(factory, evidence.retain)
        result = summarize(rows)
        result.update(mode='OFFLINE_SYNTHETIC', scientific_headroom=False, model_calls=0, spend='0')
        evidence.retain('summary', result)
        return result
    finally:
        evidence.close()


def main():
    parser = argparse.ArgumentParser(description='Step 1 offline engineering controls only')
    parser.add_argument('--offline', action='store_true', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--standin', choices=['key_following', 'cautious', 'adversarial'], default='key_following')
    args = parser.parse_args()
    print(json.dumps(offline(args.output, args.standin), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
