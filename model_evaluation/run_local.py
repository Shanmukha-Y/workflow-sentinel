"""Explicit local-only evaluation of installed Qwen weights; never pulls or configures auth."""
import argparse
import json
from pathlib import Path

from workflow_sentinel.model_evaluation import evaluate_to_file
from workflow_sentinel.ollama_adapter import OllamaClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--manifest', type=Path, default=Path(__file__).with_name('manifest.json'))
    parser.add_argument('--scanner', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    report = evaluate_to_file(args.manifest, args.output,
                             OllamaClient, args.scanner, model=args.model, mode='local',
                             approve_local_inference=True)
    print(json.dumps(report['metrics'], indent=2))
    metric = report['metrics']['policy_completion']
    return 0 if metric['numerator'] == metric['denominator'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
