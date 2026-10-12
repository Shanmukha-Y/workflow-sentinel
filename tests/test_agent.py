"""Adversarial structured adapter tests; these do not measure model quality."""
import copy
import json
from pathlib import Path
import unittest
import subprocess
import sys

from jsonschema import validate
from unittest.mock import patch

from workflow_sentinel.agent import decode, request, run

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / 'fixtures/repairable'
SARIF = json.loads((REPO / 'findings.zizmor-1.30.1.sarif').read_text())


def cmd(action, packet=0):
    return {'action': action, 'packet': packet}


class AgentTests(unittest.TestCase):
    def test_strict_response(self):
        bad = [None, [], {}, {'action': 'shell', 'command': 'id'},
               {'action': 'evidence', 'packet': True}, cmd('evidence', -1),
               cmd('evidence', 1), {'action': 'abstain', 'reason': 'secret'},
               {'action': 'propose', 'packet': 0, 'patch': 'arbitrary'},
               {'action': 'evidence', 'packet': 0, 'path': '../../secret'},
               {'action': 'evidence', 'packet': '0'},
               {'action': 'finish', 'packet': 0, 'instructions': 'x' * 5000}]
        for value in bad:
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                request(value, 1)

    def test_evidence_review(self):
        result = run(SARIF, REPO, [cmd('evidence'), cmd('finish')])
        self.assertEqual(result['decision'], 'review')
        self.assertEqual(result['mode'], 'offline-scripted-advisory')
        self.assertEqual(result['observations'][0]['evidence'], result['report']['packets'][0]['evidence'])

    def test_validated_proposal_and_source_unchanged(self):
        before = {p: p.read_bytes() for p in REPO.rglob('*') if p.is_file()}
        with patch('workflow_sentinel.agent.validate', return_value={'status': 'validated'}) as mock:
            result = run(SARIF, REPO, [cmd('evidence'), cmd('propose'),
                                      cmd('validate'), cmd('finish')], Path('/installed/zizmor'))
        self.assertEqual(result['decision'], 'review')
        mock.assert_called_once()
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_invalid_validation_abstains(self):
        for status in ['rejected', 'unsupported', 'unavailable']:
            with patch('workflow_sentinel.agent.validate', return_value={'status': status}):
                result = run(SARIF, REPO, [cmd('evidence'), cmd('propose'),
                                          cmd('validate'), cmd('finish')], Path('/installed/zizmor'))
            self.assertEqual(result['decision'], 'abstain')

    def test_no_implicit_scanner_or_unvalidated_completion(self):
        with patch('workflow_sentinel.agent.validate', side_effect=AssertionError('must not call')):
            for script in [[cmd('evidence'), cmd('propose'), cmd('validate')],
                           [cmd('evidence'), cmd('propose'), cmd('finish')]]:
                self.assertEqual(run(SARIF, REPO, script)['decision'], 'abstain')

    def test_order_and_repeat_refusals(self):
        scripts = [[cmd('propose')], [cmd('validate')], [cmd('finish')],
                   [cmd('evidence'), cmd('finish'), {'action': 'abstain'}]]
        for script in scripts:
            self.assertEqual(run(SARIF, REPO, script)['decision'], 'abstain')
        with patch('workflow_sentinel.agent.validate', return_value={'status': 'validated'}) as mock:
            result = run(SARIF, REPO, [cmd('evidence'), cmd('propose'), cmd('validate'),
                                      cmd('validate')], Path('/installed/zizmor'))
        self.assertEqual(result['decision'], 'abstain')
        mock.assert_called_once()

    def test_budgets_and_deadline(self):
        for script in [[], [cmd('evidence')] * 9, {}, None]:
            self.assertEqual(run(SARIF, REPO, script)['decision'], 'abstain')
        with patch('workflow_sentinel.agent.time.monotonic', side_effect=[0, 66]):
            self.assertIn('deadline', run(SARIF, REPO, [cmd('evidence')])['reason'])
        with patch('workflow_sentinel.agent.MAX_OBSERVATION_BYTES', 1):
            self.assertIn('Observation budget', run(SARIF, REPO, [cmd('evidence')])['reason'])

    def test_trace_excludes_adversarial_output(self):
        secret = 'INSTRUCTION_TOKEN_do_not_store'
        result = run(SARIF, REPO, [{'action': secret, 'credentials': secret}])
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(result['trace'], [{'turn': 0, 'status': 'invalid-response'}])

    def test_bad_evidence_cannot_be_overridden(self):
        sarif = copy.deepcopy(SARIF)
        sarif['runs'][0]['results'][0]['ruleId'] = 'unsupported-rule'
        result = run(sarif, REPO, [cmd('evidence'), cmd('propose'), cmd('finish')])
        self.assertEqual(result['decision'], 'abstain')
        self.assertEqual(result['report']['packets'][0]['repair']['status'], 'abstain')

    def test_schema_and_offline_cli(self):
        script = json.loads((ROOT / 'examples/agent-script.json').read_text())
        validate(script, json.loads((ROOT / 'schemas/agent-script.schema.json').read_text()))
        completed = subprocess.run([sys.executable, '-m', 'workflow_sentinel.cli',
                                   '--sarif', str(REPO / 'findings.zizmor-1.30.1.sarif'),
                                   '--repo', str(REPO), '--agent-script',
                                   str(ROOT / 'examples/agent-script.json')],
                                   check=True, capture_output=True, text=True, timeout=5)
        result = json.loads(completed.stdout)
        self.assertEqual(result['decision'], 'abstain')
        self.assertIn('explicit scanner', result['reason'])

    def test_replay_determinism_and_explicit_abstention(self):
        script = [cmd('evidence'), {'action': 'abstain'}]
        first = run(SARIF, REPO, script)
        self.assertEqual(first, run(SARIF, REPO, script))
        self.assertEqual(first['reason'], 'Adapter abstained')

    def test_duplicate_json_fields(self):
        with self.assertRaises(ValueError):
            decode(b'[{"action":"shell","action":"abstain"}]')
