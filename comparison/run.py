"""Bounded real local comparison; sequential model loading and no fake response transport."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from workflow_sentinel.model_evaluation import Budget, evaluate
from workflow_sentinel.ollama_adapter import CONTEXT, OllamaClient
from workflow_sentinel.openai_adapter import deadline

ROOT = Path(__file__).resolve().parents[1]
MODELS = ['qwen3.8:27b-q4_K_M', 'gemma4:31b-it-q4_K_M', 'mistral-small3.2:24b']
GROUPS = [('development', ROOT / 'model_evaluation/manifest.json'),
          ('exposed-contract', ROOT / 'model_evaluation/holdout-v2/manifest.json'),
          ('fresh', ROOT / 'comparison/fresh-v2/manifest.json')]


def preload(client, model):
    if client.call('/api/ps').get('models'):
        raise RuntimeError('Another model is loaded; refusing concurrent resource use')
    started = time.monotonic()
    with deadline(120):
        doc = client.call('/api/generate', {'model': model, 'prompt': '', 'stream': False,
            'keep_alive': '5m', 'options': {'num_ctx': CONTEXT}}, timeout=120)
    return {'wall_seconds': round(time.monotonic() - started, 6), 'raw_response': doc}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scanner', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    args.output_directory.mkdir()
    protocol = json.loads((ROOT / 'comparison/PROTOCOL.json').read_text())
    for name, digest in protocol['frozen_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, 'Protocol changed'
    client = OllamaClient()
    metadata = {m: client.model_info(m) for m in MODELS}
    started = time.monotonic()
    remaining_calls = 360
    rows = []
    for trial, order in [(1, MODELS), (2, list(reversed(MODELS)))]:
        for model in order:
            if time.monotonic() - started > 2700:
                raise RuntimeError('Comparison wall budget exhausted; completed records retained')
            cold = preload(client, model)
            run_groups = GROUPS if trial == 1 else [GROUPS[-1]]
            try:
                for group, manifest in run_groups:
                    remaining = 2700 - (time.monotonic() - started)
                    ledger = Budget(max_calls=min(32, remaining_calls), seconds=min(540, remaining))
                    report = evaluate(manifest, OllamaClient, args.scanner, model=model, mode='local',
                                      approve_local_inference=True, capture_raw_evidence=True,
                                      budget=ledger)
                    remaining_calls -= ledger.reserved
                    report['comparison'] = {'trial': trial, 'group': group,
                        'cold_preload': cold, 'model_metadata': metadata[model],
                        'role': 'first-exposure' if trial == 1 and group == 'fresh' else 'exposed'}
                    stem = model.replace(':', '-').replace('.', '_') + '-' + group + '-t' + str(trial)
                    with (args.output_directory / (stem + '.json')).open('x') as stream:
                        json.dump(report, stream, indent=2, sort_keys=True)
                        stream.write('\n')
                    entry = {'file': stem + '.json', 'model': model, 'trial': trial, 'group': group,
                             'metrics': report['metrics'], 'wall_seconds': report['wall_seconds']}
                    rows.append(entry)
                    print(json.dumps(entry), flush=True)
            finally:
                with deadline(30):
                    client.call('/api/generate', {'model': model, 'prompt': '', 'stream': False,
                                                'keep_alive': 0}, timeout=30)
                with deadline(30):
                    while client.call('/api/ps').get('models'):
                        time.sleep(0.25)
    with (args.output_directory / 'index.json').open('x') as stream:
        json.dump({'protocol': protocol, 'models': metadata, 'rows': rows,
                   'wall_seconds': round(time.monotonic()-started, 6),
                   'reserved_requests': 360 - remaining_calls}, stream, indent=2)
        stream.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
