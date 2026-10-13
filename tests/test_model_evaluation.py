"""Model harness scoring/budget regressions; no live API calls."""
import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx2

from workflow_sentinel.agent import run
from workflow_sentinel.model_evaluation import (
    Budget, evaluate, evaluate_to_file, manifest, ratio, save, score,
)
from workflow_sentinel.openai_adapter import OpenAIAdapter

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'model_evaluation/manifest.json'
SPEC = importlib.util.spec_from_file_location('model_mock', ROOT / 'model_evaluation/run_mock.py')
MOCK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOCK)


def fake_scan(packet, root, scanner):
    return {'status': 'validated', 'target_removed': True, 'new_findings': 0, 'attempts': 2}


class ModelEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.doc = manifest(MANIFEST)

    def report(self, case, script):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            p = repo / self.doc['path']
            p.parent.mkdir(parents=True)
            p.write_text(case['source'])
            with patch('workflow_sentinel.agent.validate', side_effect=fake_scan):
                return run(case['sarif'], repo, script, Path('/mock/zizmor'))

    def test_offline_oracle_no_quality_claim(self):
        with patch('workflow_sentinel.agent.validate', side_effect=fake_scan):
            result = evaluate(MANIFEST, MOCK.mock_client, Path('/mock/zizmor'), model='mock-model')
        self.assertEqual(result['metrics']['policy_completion'], ratio(8, 8))
        self.assertEqual(result['metrics']['provider_attempts'], 23)
        self.assertEqual(result['budget']['reserved_attempts'], 23)
        self.assertEqual(result['budget']['max_output_tokens_total'], 8192)
        self.assertEqual(result['mode'], 'mock')
        self.assertTrue(result['cases'][-1]['attack_text_in_confirmed_request'])
        self.assertTrue(all(c['source_unchanged'] for c in result['cases']))
        self.assertIn('Mock scores do not measure real model quality', result['limitations'])

    def test_all_abstainer_is_not_perfect(self):
        for case in self.doc['cases']:
            report = self.report(case, [{'action': 'abstain'}])
            got = score(case, report, True)['passed']
            self.assertEqual(got, case['expected'] == 'abstain')
        self.assertEqual(sum(c['expected'] == 'abstain' for c in self.doc['cases']), 2)

    def test_timeout_or_protocol_error_is_not_correct_abstention(self):
        case = self.doc['cases'][5]
        report = self.report(case, [{'action': 'abstain'}])
        report['trace'] = [{'turn': 0, 'status': 'adapter-error'}]
        self.assertFalse(score(case, report, True)['passed'])
        report['trace'] = [{'turn': 0, 'status': 'invalid-response'}, {'action': 'abstain'}]
        self.assertFalse(score(case, report, True)['passed'])

    def test_early_finish_not_useful_repair_or_manual_review(self):
        for case in self.doc['cases'][:5]:
            report = self.report(case, [{'action': 'evidence', 'packet': 0},
                                        {'action': 'finish', 'packet': 0}])
            self.assertFalse(score(case, report, True)['passed'])

    def test_golden_source_citations_and_source_immutability(self):
        case = self.doc['cases'][0]
        script = [{'action': a, 'packet': 0} for a in ['evidence', 'propose', 'validate', 'finish']]
        report = self.report(case, script)
        self.assertTrue(score(case, report, True)['passed'])
        self.assertFalse(score(case, report, False)['passed'])
        bad = copy.deepcopy(case)
        bad['candidate_source'] += '# different\n'
        self.assertFalse(score(bad, report, True)['passed'])
        for key, value in [('sha256', 'tampered'), ('citation', 'wrong'), ('excerpt', 'wrong'),
                           ('column', 9999), ('yaml_path', ['wrong'])]:
            altered = copy.deepcopy(report)
            altered['observations'][0]['evidence'][0][key] = value
            self.assertFalse(score(case, altered, True)['passed'], key)

    def test_multiline_excerpt_and_confirmed_attack_exposure(self):
        case = self.doc['cases'][-1]
        report = self.report(case, [{'action': a, 'packet': 0}
                                    for a in ['evidence', 'propose', 'finish']])
        self.assertFalse(score(case, report, True, 0)['passed'])
        result = score(case, report, True, 1)
        self.assertTrue(result['passed'])
        self.assertEqual(result['citations'], ratio(1, 1))
        self.assertTrue(result['attack_text_in_confirmed_request'])

    def test_budget_skips_remain_in_denominator(self):
        result = evaluate(MANIFEST, MOCK.mock_client, None, model='mock-model',
                          budget=Budget(max_calls=1))
        self.assertEqual(result['metrics']['policy_completion']['denominator'], 8)
        self.assertEqual(result['metrics']['cases_not_run'], 7)
        self.assertEqual(result['metrics']['provider_attempts'], 1)
        self.assertEqual(result['metrics']['policy_completion']['numerator'], 0)
        with patch('workflow_sentinel.model_evaluation.Budget.remaining', return_value=0):
            result = evaluate(MANIFEST, lambda: self.fail('no client after deadline'), None,
                              model='mock-model')
        self.assertEqual(result['metrics']['cases_not_run'], 8)

    def test_failed_calls_consume_budget_and_sanitize_errors(self):
        def factory():
            return MOCK.mock_client(lambda req: httpx2.Response(503, json={
                'error': {'message': 'PRIVATE_RESPONSE_SHOULD_NOT_BE_SAVED'}}))
        result = evaluate(MANIFEST, factory, None, model='mock-model',
                          budget=Budget(max_calls=1))
        self.assertTrue(result['cases'][0]['provider_or_protocol_error'])
        self.assertEqual(result['budget']['reserved_attempts'], 1)
        self.assertEqual(result['metrics']['provider_attempts'], 1)
        self.assertEqual(result['metrics']['policy_completion'], ratio(0, 8))
        self.assertNotIn('PRIVATE_RESPONSE_SHOULD_NOT_BE_SAVED', json.dumps(result))

    def test_live_approval_and_config_preflight_never_construct_client(self):
        def factory():
            self.fail('client must not be constructed')
        for flags in [{}, {'approve_live_calls': True}, {'approve_source_disclosure': True}]:
            with self.assertRaises(ValueError):
                evaluate(MANIFEST, factory, None, model='mock-model', mode='live', **flags)
        for kwargs in [{'tokens': True}, {'tokens': 257}, {'model': ''},
                       {'budget': Budget(max_calls=33)}, {'budget': Budget(seconds=541)}]:
            with self.assertRaises(ValueError):
                evaluate(MANIFEST, factory, None, **{'model': 'mock-model', **kwargs})

    def test_manifest_integrity_and_exclusive_output(self):
        self.assertEqual(len(self.doc['cases']), 8)
        self.assertIn('not held-out', self.doc['methodology'])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'manifest.json'
            target.write_bytes(MANIFEST.read_bytes() + b' ')
            target.with_name('FREEZE.json').write_bytes(MANIFEST.with_name('FREEZE.json').read_bytes())
            with self.assertRaisesRegex(ValueError, 'integrity'):
                manifest(target)
            output = Path(directory) / 'report.json'
            save({'mode': 'mock'}, output)
            with self.assertRaises(FileExistsError):
                save({'mode': 'live'}, output)
            self.assertEqual(json.loads(output.read_text()), {'mode': 'mock'})
        self.assertIsNone(ratio(0, 0)['value'])

    def test_harness_errors_and_client_cleanup_are_failures(self):
        def broken():
            raise RuntimeError('SECRET_FACTORY_ERROR')
        result = evaluate(MANIFEST, broken, None, model='mock-model')
        self.assertEqual(result['metrics']['harness_errors'], 8)
        self.assertEqual(result['metrics']['policy_completion'], ratio(0, 8))
        self.assertNotIn('SECRET_FACTORY_ERROR', json.dumps(result))

    def test_per_case_call_cap_with_real_sdk_mock(self):
        def factory():
            count = 0

            def handler(req):
                nonlocal count
                count += 1
                return httpx2.Response(200, json={'id': 'resp_mock', 'object': 'response',
                    'created_at': 0, 'model': 'mock-model', 'status': 'completed', 'output': [
                        {'id': 'fc_mock', 'type': 'function_call', 'call_id': 'call_' + str(count),
                         'name': 'evidence', 'arguments': '{"packet":0}', 'status': 'completed'}]})
            return MOCK.mock_client(handler)
        result = evaluate(MANIFEST, factory, None, model='mock-model')
        self.assertTrue(all(c['provider_attempts'] <= 4 for c in result['cases']))
        self.assertLessEqual(result['budget']['reserved_attempts'], 32)
        self.assertEqual(result['metrics']['policy_completion'], ratio(0, 8))

    def test_provider_history_not_saved(self):
        client = MOCK.mock_client()
        try:
            adapter = OpenAIAdapter(client, model='mock-model', max_output_tokens=256,
                                    allow_source_disclosure=True)
            self.assertEqual(adapter.mode, 'openai-advisory')
        finally:
            client.close()
        with patch('workflow_sentinel.agent.validate', side_effect=fake_scan):
            result = evaluate(MANIFEST, MOCK.mock_client, Path('/mock/zizmor'), model='mock-model')
        text = json.dumps(result)
        self.assertNotIn('mock-placeholder-not-a-credential', text)
        self.assertNotIn('SENTINEL_EVAL_ATTACK', text)
        self.assertNotIn('github.event.pull_request.title', text)

    def test_missing_usage_is_unknown_not_zero(self):
        with patch('workflow_sentinel.agent.validate', side_effect=fake_scan):
            result = evaluate(MANIFEST, MOCK.mock_client, Path('/mock/zizmor'), model='mock-model')
        self.assertEqual(result['usage']['unknown_requests'], 23)
        self.assertEqual(result['usage']['known_requests'], 0)
        self.assertEqual(result['usage']['input_tokens_known'], 0)

    def test_known_usage_and_over_cap_failure(self):
        def factory():
            client = MOCK.mock_client()
            original = client._client._transport

            def handler(req):
                reply = original.handle_request(req)
                doc = json.loads(reply.content)
                doc['usage'] = {'input_tokens': 10, 'output_tokens': 5, 'total_tokens': 15,
                                'input_tokens_details': {'cached_tokens': 0},
                                'output_tokens_details': {'reasoning_tokens': 0}}
                return httpx2.Response(200, json=doc)
            client._client._transport = httpx2.MockTransport(handler)
            return client
        with patch('workflow_sentinel.agent.validate', side_effect=fake_scan):
            result = evaluate(MANIFEST, factory, Path('/mock/zizmor'), model='mock-model')
        self.assertEqual(result['usage'], {'known_requests': 23, 'unknown_requests': 0,
                                          'input_tokens_known': 230, 'output_tokens_known': 115})

        def over_cap():
            return MOCK.mock_client(lambda req: httpx2.Response(200, json={
                'status': 'completed', 'output': [], 'usage': {'input_tokens': 10,
                                                               'output_tokens': 1000}}))
        result = evaluate(MANIFEST, over_cap, None, model='mock-model', budget=Budget(max_calls=1))
        self.assertFalse(result['cases'][0]['passed'])
        self.assertEqual(result['usage']['output_tokens_known'], 1000)

    def test_preserved_original_and_corrected_records(self):
        history = json.loads((ROOT / 'model_evaluation/HISTORY.json').read_text())
        for name, expected in history['records_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / 'model_evaluation/results' / name)
                                           .read_bytes()).hexdigest(), expected)
        original = json.loads((ROOT / 'model_evaluation/results/mock-first-scoring-error.json')
                              .read_text())
        corrected = json.loads((ROOT / 'model_evaluation/results/mock-regression.json').read_text())
        self.assertEqual(original['metrics']['policy_completion'], ratio(7, 8))
        self.assertEqual(corrected['metrics']['policy_completion'], ratio(8, 8))
        self.assertEqual(corrected['mode'], 'mock')

    def test_client_cleanup_error_is_recorded(self):
        def factory():
            client = MOCK.mock_client()
            original_close = client.close

            def close():
                original_close()
                raise RuntimeError('PRIVATE_CLEANUP_ERROR')
            client.close = close
            return client
        result = evaluate(MANIFEST, factory, None, model='mock-model')
        self.assertEqual(result['metrics']['harness_errors'], 8)
        self.assertTrue(all(c['status'] == 'client-cleanup-error' for c in result['cases']))
        self.assertNotIn('PRIVATE_CLEANUP_ERROR', json.dumps(result))

    def test_output_reservation_precedes_provider_work(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'run.json'
            output.write_text('original')
            with self.assertRaises(FileExistsError):
                evaluate_to_file(MANIFEST, output, lambda: self.fail('no provider call'),
                                 None, model='mock-model')
            self.assertEqual(output.read_text(), 'original')
            fresh = Path(directory) / 'aborted.json'
            with self.assertRaises(ValueError):
                evaluate_to_file(MANIFEST, fresh, lambda: self.fail('no provider call'),
                                 None, model='')
            self.assertEqual(json.loads(fresh.read_text())['status'], 'run-aborted')
