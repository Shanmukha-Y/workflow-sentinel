"""Run only the in-memory SDK policy oracle; no live transport or credential configuration."""
import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

import httpx2
from openai import OpenAI

from workflow_sentinel.model_evaluation import evaluate_to_file


def mock_client(handler_override=None):
    counter = 0

    def handler(req):
        nonlocal counter
        counter += 1
        payload = json.loads(req.content)
        last = payload['input'][-1]
        if last.get('type') != 'function_call_output':
            action = 'evidence' if json.loads(last['content'])['packets'] else 'abstain'
        else:
            obs = json.loads(last['output'])
            if obs['action'] == 'evidence':
                action = 'propose' if obs['decision'] == 'review' else 'abstain'
            elif obs['action'] == 'propose':
                action = 'validate' if obs['repair']['status'] == 'proposed' else 'finish'
            else:
                action = 'finish' if obs['static_validation']['status'] == 'validated' else 'abstain'
        return httpx2.Response(200, json={'id': 'resp_mock', 'object': 'response', 'created_at': 0,
            'status': 'completed', 'model': 'mock-model', 'output': [{'id': 'fc_mock',
            'type': 'function_call', 'call_id': 'call_' + str(counter), 'name': action,
            'arguments': json.dumps({} if action == 'abstain' else {'packet': 0}),
            'status': 'completed'}]})

    with patch.dict(os.environ, {}, clear=True):
        return OpenAI(api_key='mock-placeholder-not-a-credential',
                      http_client=httpx2.Client(transport=httpx2.MockTransport(handler_override or handler)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scanner', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = evaluate_to_file(Path(__file__).with_name('manifest.json'), args.output,
                              mock_client, args.scanner, model='mock-model')
    print(json.dumps(report['metrics'], indent=2))
    return 0 if report['metrics']['policy_completion']['numerator'] == 8 else 1


if __name__ == '__main__':
    raise SystemExit(main())
