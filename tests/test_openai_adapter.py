"""Real SDK wire protocol over an in-memory transport; never live model evaluation."""
import copy
import json
import os
from pathlib import Path
import signal
import time
import unittest
from unittest.mock import patch

import httpx2
from openai import OpenAI

from workflow_sentinel.agent import run
from workflow_sentinel.openai_adapter import OpenAIAdapter, ProviderError, deadline

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / 'fixtures/repairable'
SARIF = json.loads((REPO / 'findings.zizmor-1.30.1.sarif').read_text())


def response(action='abstain', arguments=None):
    return {'id': 'resp_mock', 'object': 'response', 'created_at': 0,
            'status': 'completed', 'model': 'mock-model', 'output': [
                {'id': 'fc_mock', 'type': 'function_call', 'call_id': 'call_mock',
                 'name': action, 'arguments': json.dumps(arguments or {}), 'status': 'completed'}]}


class ProviderTests(unittest.TestCase):
    def client(self, handler):
        # Fixed mock placeholder and empty environment; no real credential discovery.
        with patch.dict(os.environ, {}, clear=True):
            client = OpenAI(api_key='mock-placeholder-not-a-credential',
                            http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))
        self.addCleanup(client.close)
        return client

    def adapter(self, handler):
        return OpenAIAdapter(self.client(handler), model='mock-model', max_output_tokens=256,
                             allow_source_disclosure=True)

    def test_interactive_wire_protocol_and_validation(self):
        requests = []
        actions = iter(['evidence', 'propose', 'validate', 'finish'])

        def handler(req):
            requests.append(json.loads(req.content))
            action = next(actions)
            doc = response(action, {'packet': 0})
            doc['output'][0]['call_id'] = 'call_' + str(len(requests))
            return httpx2.Response(200, json=doc)

        adapter = self.adapter(handler)
        with patch('workflow_sentinel.agent.validate', return_value={'status': 'validated'}):
            result = run(SARIF, REPO, None, Path('/installed/zizmor'), adapter=adapter)
        self.assertEqual(result['decision'], 'review')
        self.assertEqual(result['mode'], 'openai-advisory')
        self.assertEqual(len(requests), 4)
        self.assertEqual(requests[1]['input'][-1]['type'], 'function_call_output')
        self.assertEqual(requests[1]['input'][-1]['call_id'], 'call_1')
        self.assertEqual(json.loads(requests[1]['input'][-1]['output'])['action'], 'evidence')
        self.assertIn('untrusted data', requests[0]['instructions'])
        for req in requests:
            self.assertFalse(req['store'])
            self.assertFalse(req['parallel_tool_calls'])
            self.assertEqual(req['tool_choice'], 'required')
            self.assertEqual(req['max_output_tokens'], 256)
            self.assertEqual({t['name'] for t in req['tools']},
                             {'evidence', 'propose', 'validate', 'finish', 'abstain'})
            self.assertTrue(all(t['strict'] for t in req['tools']))

    def test_opt_in_configuration(self):
        client = self.client(lambda req: self.fail('network must not be called'))
        for kwargs in [{}, {'allow_source_disclosure': True, 'max_output_tokens': True},
                       {'allow_source_disclosure': True, 'model': ''},
                       {'allow_source_disclosure': True, 'max_output_tokens': 513}]:
            options = {'model': 'mock-model', 'max_output_tokens': 256, **kwargs}
            with self.assertRaises(ProviderError):
                OpenAIAdapter(client, **options)
        client.base_url = 'https://example.invalid/v1'
        with self.assertRaises(ProviderError):
            OpenAIAdapter(client, model='mock-model', max_output_tokens=256,
                          allow_source_disclosure=True)

    def test_failure_sanitization_no_retries(self):
        count = 0

        def handler(req):
            nonlocal count
            count += 1
            return httpx2.Response(429, json={'error': {'message': 'private_body_do_not_record'}})

        result = run(SARIF, REPO, None, adapter=self.adapter(handler))
        self.assertEqual(count, 1)
        self.assertEqual(result['decision'], 'abstain')
        self.assertNotIn('private_body_do_not_record', json.dumps(result))
        self.assertEqual(result['trace'][0]['status'], 'adapter-error')

    def test_adversarial_and_refused_protocol(self):
        docs = []
        for action, arguments in [('shell', {}), ('propose', {'packet': 0, 'patch': 'x'}),
                                  ('evidence', {'packet': True}), ('evidence', {'packet': -1})]:
            docs.append(response(action, arguments))
        for status in ['incomplete', 'failed', 'cancelled']:
            doc = response()
            doc['status'] = status
            docs.append(doc)
        doc = response()
        doc['output'].append(copy.deepcopy(doc['output'][0]))
        docs.append(doc)
        doc = response()
        doc['output'] = [{'type': 'message', 'content': [{'type': 'refusal', 'refusal': 'secret'}]}]
        docs.append(doc)
        doc = response('evidence')
        doc['output'][0]['arguments'] = '{"packet":0,"packet":0}'
        docs.append(doc)
        doc = response()
        doc['output'][0]['arguments'] = 'x' * 5000
        docs.append(doc)
        for doc in docs:
            with self.subTest(doc=doc['status']):
                adapter = self.adapter(lambda req: httpx2.Response(200, json=doc))
                self.assertEqual(run(SARIF, REPO, None, adapter=adapter)['decision'], 'abstain')

    def test_real_wall_timeout_and_timer_restore(self):
        def handler(req):
            time.sleep(0.2)
            return httpx2.Response(200, json=response())
        previous = signal.getsignal(signal.SIGALRM)
        with patch('workflow_sentinel.openai_adapter.CALL_SECONDS', 0.02):
            result = run(SARIF, REPO, None, adapter=self.adapter(handler))
        self.assertEqual(result['decision'], 'abstain')
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0, 0))
        with self.assertRaises(ProviderError), deadline(0):
            self.fail('expired deadline entered')

    def test_input_output_and_call_bounds(self):
        counter = 0

        def handler(req):
            nonlocal counter
            counter += 1
            doc = response('evidence', {'packet': 0})
            doc['output'][0]['call_id'] = 'call_' + str(counter)
            return httpx2.Response(200, json=doc)
        adapter = self.adapter(handler)
        result = run(SARIF, REPO, None, adapter=adapter)
        self.assertEqual(result['decision'], 'abstain')
        self.assertEqual(adapter.calls, 8)
        adapter = self.adapter(handler)
        with patch('workflow_sentinel.openai_adapter.MAX_INPUT_BYTES', 1):
            result = run(SARIF, REPO, None, adapter=adapter)
        self.assertEqual(adapter.calls, 0)
        self.assertEqual(result['decision'], 'abstain')
        adapter = self.adapter(handler)
        with patch('workflow_sentinel.openai_adapter.MAX_PROVIDER_BYTES', 1):
            result = run(SARIF, REPO, None, adapter=adapter)
        self.assertEqual(result['decision'], 'abstain')

    def test_reasoning_continuation_and_no_implicit_scanner(self):
        requests = []
        actions = iter(['evidence', 'propose', 'validate'])

        def handler(req):
            requests.append(json.loads(req.content))
            doc = response(next(actions), {'packet': 0})
            doc['output'][0]['call_id'] = 'call_' + str(len(requests))
            doc['output'].insert(0, {'type': 'reasoning', 'id': 'rs_mock', 'summary': []})
            return httpx2.Response(200, json=doc)
        with patch('workflow_sentinel.agent.validate', side_effect=AssertionError('no opt-in')):
            result = run(SARIF, REPO, None, adapter=self.adapter(handler))
        self.assertEqual(result['decision'], 'abstain')
        self.assertEqual(requests[1]['input'][1]['type'], 'reasoning')

    def test_duplicate_call_ids_and_conflicting_timer(self):
        adapter = self.adapter(lambda req: httpx2.Response(
            200, json=response('evidence', {'packet': 0})))
        result = run(SARIF, REPO, None, adapter=adapter)
        self.assertEqual(result['decision'], 'abstain')
        self.assertEqual(adapter.calls, 2)
        signal.setitimer(signal.ITIMER_REAL, 5)
        try:
            with self.assertRaises(ProviderError), deadline(1):
                self.fail('conflicting alarm entered')
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
