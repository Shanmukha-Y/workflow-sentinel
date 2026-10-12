"""In-memory SDK demo: no live API calls, credential discovery or model-quality claim."""
import argparse
import json
import os
from pathlib import Path
from unittest.mock import patch

import httpx2
from openai import OpenAI

from workflow_sentinel.agent import run
from workflow_sentinel.openai_adapter import OpenAIAdapter

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scanner', type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / 'fixtures/repairable'
counter = 0


def handler(req):
    global counter
    counter += 1
    payload = json.loads(req.content)
    last = payload['input'][-1]
    observation = json.loads(last['output']) if last.get('type') == 'function_call_output' else {}
    previous = observation.get('action')
    action = {None: 'evidence', 'evidence': 'propose', 'propose': 'validate'}.get(previous)
    if previous == 'validate':
        action = 'finish' if observation['static_validation']['status'] == 'validated' else 'abstain'
    arguments = {} if action == 'abstain' else {'packet': 0}
    return httpx2.Response(200, json={
        'id': 'resp_mock', 'object': 'response', 'created_at': 0, 'status': 'completed',
        'model': 'mock-model', 'output': [{'id': 'fc_mock', 'type': 'function_call',
                                         'call_id': 'call_' + str(counter), 'name': action,
                                         'arguments': json.dumps(arguments), 'status': 'completed'}]})


with patch.dict(os.environ, {}, clear=True):
    client = OpenAI(api_key='mock-placeholder-not-a-credential',
                    http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
with client:
    adapter = OpenAIAdapter(client, model='mock-model', max_output_tokens=256,
                            allow_source_disclosure=True)
    result = run(json.loads((root / 'findings.zizmor-1.30.1.sarif').read_text()),
                 root, None, args.scanner, adapter=adapter)
    result['mode'] = 'mock-openai-transport-advisory'
    print(json.dumps(result, indent=2))
