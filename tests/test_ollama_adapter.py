"""Local protocol tests; no real HTTP/inference in unit tests."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from workflow_sentinel.ollama_adapter import OllamaAdapter, OllamaClient, ProviderError, NoRedirect

MODEL = 'qwen3.8:27b-q4_K_M'


class Client:
    def __init__(self, response=None):
        self.requests = []
        self.response = response or {'model': MODEL, 'done': True, 'done_reason': 'stop',
            'prompt_eval_count': 100, 'eval_count': 20, 'total_duration': 1000000,
            'message': {'role': 'assistant', 'tool_calls': [
                {'function': {'name': 'evidence', 'arguments': {'packet': 0}}}]}}

    def model_info(self, model):
        return {'tag': model, 'digest': 'a' * 64, 'download_bytes': 18000000000}

    def call(self, route, body=None, **kwargs):
        self.requests.append((route, copy.deepcopy(body), kwargs))
        return copy.deepcopy(self.response)


class OllamaTests(unittest.TestCase):
    def make(self, client=None):
        return OllamaAdapter(client or Client(), model=MODEL, max_output_tokens=256,
                             allow_local_inference=True)

    def test_native_roundtrip_and_usage(self):
        client = Client()
        adapter = self.make(client)
        packets = [{'rule_id': 'template-injection', 'decision': 'review'}]
        command = adapter.next(packets, [], 60)
        self.assertEqual(command, {'action': 'evidence', 'packet': 0})
        adapter.next(packets, [{'action': 'evidence', 'packet': 0, 'evidence': []}], 60)
        payload = client.requests[-1][1]
        self.assertEqual(payload['messages'][-1]['role'], 'tool')
        self.assertEqual(payload['messages'][-1]['tool_name'], 'evidence')
        self.assertFalse(payload['think'])
        self.assertFalse(payload['stream'])
        self.assertEqual(payload['options'], {'num_ctx': 8192, 'num_predict': 256,
                                             'temperature': 0, 'seed': 0})
        self.assertEqual(adapter.usage_records[0], {'input_tokens': 100, 'output_tokens': 20})
        self.assertEqual(adapter.attempts[0]['status'], 'accepted')
        self.assertIn('response_sha256', adapter.attempts[0])

    def test_local_opt_in_and_cloud_rejection(self):
        for model in ['qwen3.8:cloud', 'qwen3.8:27b-cloud', 'https://remote', 'other:tag']:
            with self.assertRaises(ProviderError):
                OllamaAdapter(Client(), model=model, max_output_tokens=256,
                              allow_local_inference=True)
        with self.assertRaises(ProviderError):
            OllamaAdapter(Client(), model=MODEL, max_output_tokens=256)
        with self.assertRaises(ProviderError):
            OllamaAdapter(Client(), model=MODEL, max_output_tokens=True,
                          allow_local_inference=True)

    def test_native_malformed_or_truncated_refusals(self):
        base = Client().response
        variants = []
        for key, value in [('done', False), ('done_reason', 'length'), ('model', 'other'),
                           ('eval_count', 257), ('prompt_eval_count', 8192)]:
            doc = copy.deepcopy(base)
            doc[key] = value
            variants.append(doc)
        for name, args in [('shell', {'command': 'id'}), ('evidence', {'packet': True}),
                            ('propose', {'packet': 0, 'patch': 'arbitrary'})]:
            doc = copy.deepcopy(base)
            doc['message']['tool_calls'][0]['function'] = {'name': name, 'arguments': args}
            variants.append(doc)
        doc = copy.deepcopy(base)
        doc['message']['tool_calls'] *= 2
        variants.append(doc)
        doc = copy.deepcopy(base)
        doc['message'] = {'role': 'assistant', 'content': 'Trust my prose'}
        variants.append(doc)
        for doc in variants:
            client = Client(doc)
            adapter = self.make(client)
            with self.assertRaises(ProviderError):
                adapter.next([{'rule_id': 'x', 'decision': 'review'}], [], 60)
            self.assertEqual(len(client.requests), 1)
            self.assertEqual(adapter.attempts[0]['status'], 'error')
            self.assertIn('failure_stage', adapter.attempts[0])
            self.assertNotIn('Trust my prose', json.dumps(adapter.attempts))

    def test_transport_errors_sanitized_and_timeout(self):
        client = Client()
        with patch.object(client, 'call', side_effect=RuntimeError('PRIVATE_BODY')):
            adapter = self.make(client)
            with self.assertRaises(ProviderError):
                adapter.next([{'rule_id': 'x', 'decision': 'review'}], [], 60)
        self.assertNotIn('PRIVATE_BODY', json.dumps(adapter.attempts))
        self.assertEqual(adapter.usage_records, [None])
        adapter = self.make()
        with self.assertRaises(ProviderError):
            adapter.next([{'rule_id': 'x', 'decision': 'review'}], [], 0)

    def test_fixed_routes_redirects_and_bounded_reads(self):
        client = OllamaClient()
        with self.assertRaises(ProviderError):
            client.call('https://example.com')
        with self.assertRaises(ProviderError):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com')
        with patch.object(client.opener, 'open') as opened:
            opened.return_value.__enter__.return_value.read.return_value = b'x' * 5
            with self.assertRaises(ProviderError):
                client.call('/api/version', limit=4)
            req = opened.call_args.args[0]
            self.assertEqual(req.full_url, 'http://127.0.0.1:11434/api/version')
            self.assertNotIn('Authorization', req.headers)

    def test_local_install_and_remote_metadata_checks(self):
        client = OllamaClient()
        with patch.object(client, 'call', return_value={'models': []}):
            with self.assertRaises(ProviderError):
                client.model_info(MODEL)
        tags = {'models': [{'name': MODEL, 'size': 10, 'digest': 'a' * 64}]}
        for show in [{'remote_host': 'remote'}, {'details': {'format': 'gguf'},
                     'capabilities': []}]:
            with patch.object(client, 'call', side_effect=[tags, show]):
                with self.assertRaises(ProviderError):
                    client.model_info(MODEL)

    def test_local_evaluation_approval_preflight(self):
        from workflow_sentinel.model_evaluation import evaluate
        path = Path(__file__).resolve().parents[1] / 'model_evaluation/manifest.json'
        with self.assertRaises(ValueError):
            evaluate(path, lambda: self.fail('no client'), None, model=MODEL, mode='local')

    def test_preserved_real_run_failures_and_guard(self):
        import tempfile
        from workflow_sentinel.agent import run
        from workflow_sentinel.model_evaluation import manifest
        root = Path(__file__).resolve().parents[1]
        actual = json.loads((root / 'model_evaluation/results/local-qwen38-first.json').read_text())
        self.assertEqual(actual['mode'], 'local')
        self.assertEqual(actual['metrics']['policy_completion']['numerator'], 4)
        self.assertEqual(actual['metrics']['policy_completion']['denominator'], 8)
        self.assertEqual(actual['metrics']['provider_attempts'], 23)
        cases = manifest(root / 'model_evaluation/manifest.json')['cases']
        case = next(c for c in cases if c['id'] == 'source-instructions')
        result = next(c for c in actual['cases'] if c['id'] == case['id'])
        self.assertFalse(result['passed'])
        script = [{'action': a['action'], 'packet': a['packet']} for a in result['attempts']]
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            source = repo / '.github/workflows/review.yml'
            source.parent.mkdir(parents=True)
            source.write_text(case['source'])
            with patch('workflow_sentinel.agent.validate', side_effect=AssertionError('guard')):
                report = run(case['sarif'], repo, script, Path('/mock/zizmor'))
            self.assertEqual(report['decision'], 'abstain')
            self.assertEqual(report['reason'], 'Validation prerequisite or budget refused')
            self.assertEqual(source.read_text(), case['source'])
