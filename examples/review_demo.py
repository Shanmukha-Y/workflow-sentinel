"""Consolidated synthetic review demo; no target execution or automatic patch application."""
import argparse
import hashlib
import json
from pathlib import Path

from workflow_sentinel.agent import run
from workflow_sentinel.cli import investigate
from workflow_sentinel.ollama_adapter import OllamaAdapter, OllamaClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scanner', type=Path, required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    parser.add_argument('--local-model', required=True, help='explicit opt-in to installed local Qwen inference')
    args = parser.parse_args()
    args.output_directory.mkdir()  # Fresh directory before any provider/scanner work.
    root = Path(__file__).resolve().parents[1]
    repo = root / 'fixtures/repairable'
    source = repo / '.github/workflows/review.yml'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    sarif = json.loads((repo / 'findings.zizmor-1.30.1.sarif').read_text())
    artifacts = {'review': investigate(sarif, repo),
                 'preview': investigate(sarif, repo, preview_repairs=True)}
    client = None
    try:
        client = OllamaClient()
        adapter = OllamaAdapter(client, model=args.local_model, max_output_tokens=256,
                                allow_local_inference=True)
        report = run(sarif, repo, args.scanner, adapter=adapter)
        artifacts['agent'] = report
    finally:
        if client:
            client.close()
    after = hashlib.sha256(source.read_bytes()).hexdigest()
    passed = (report['decision'] == 'review' and before == after
              and report['report']['packets'][0].get('static_validation', {}).get('status')
              == 'validated')
    artifacts['summary'] = {'mode': report['mode'], 'source_before_sha256': before,
                            'source_after_sha256': after, 'source_unchanged': before == after,
                            'static_validation_passed': passed,
                            'automatic_application': False,
                            'limitations': 'One known synthetic fixture; static validation '
                                           'does not prove security or model quality'}
    for name, doc in artifacts.items():
        with (args.output_directory / (name + '.json')).open('x') as stream:
            json.dump(doc, stream, indent=2, sort_keys=True)
            stream.write('\n')
    print(json.dumps(artifacts['summary'], indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
