"""Run only the in-memory SDK policy oracle; no live transport or credential configuration."""
import json
import os
from unittest.mock import patch

import httpx2
from openai import OpenAI



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
