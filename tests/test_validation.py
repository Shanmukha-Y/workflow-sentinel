import copy
import json
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import validate as validate_schema

from workflow_sentinel.cli import investigate
from workflow_sentinel.validation import (
    SCANNER_ARGS, ComparisonUnsupported, ScannerUnavailable, findings, scan, scanner_path, validate,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/repairable'
SOURCE = (FIXTURE / '.github/workflows/review.yml').read_text()
BEFORE = json.loads((FIXTURE / 'findings.zizmor-1.30.1.sarif').read_text())
AFTER = json.loads((FIXTURE / 'fixed.findings.zizmor-1.30.1.sarif').read_text())


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / '.github/workflows/review.yml'
        self.source.parent.mkdir(parents=True)
        self.source.write_text(SOURCE)
        self.packet = investigate(BEFORE, self.root, preview_repairs=True)['packets'][0]

    def run_validation(self, outputs=None):
        with patch('workflow_sentinel.validation.scanner_path', return_value=Path('/installed/zizmor')):
            with patch('workflow_sentinel.validation.scan', side_effect=outputs or [BEFORE, AFTER]) as mock:
                result = validate(self.packet, self.root, None)
                return result, mock.call_count

    def test_success_disposable_snapshots_and_original_unchanged(self):
        observed = []

        def scanner(executable, directory):
            observed.append((executable, directory,
                             (directory / '.github/workflows/review.yml').read_text()))
            self.assertEqual(sorted(p.name for p in directory.iterdir()), ['.github'])
            return BEFORE if len(observed) == 1 else AFTER

        with patch('workflow_sentinel.validation.scanner_path', return_value=Path('/installed/zizmor')):
            with patch('workflow_sentinel.validation.scan', side_effect=scanner):
                result = validate(self.packet, self.root, None)
        self.assertEqual(result['status'], 'validated')
        self.assertEqual(result['before_findings'], 1)
        self.assertEqual(result['after_findings'], 0)
        self.assertTrue(result['target_removed'])
        self.assertEqual(result['attempts'], 2)
        self.assertEqual(self.source.read_text(), SOURCE)
        self.assertEqual(observed[0][2], SOURCE)
        self.assertEqual(observed[1][2], (FIXTURE / 'expected-fixed.yml').read_text())
        self.assertTrue(all(not directory.exists() for _, directory, _ in observed))

    def test_source_and_diff_tampering_rejected_before_scanning(self):
        for field in ['unified_diff', 'base_sha256', 'proposed_sha256', 'path']:
            with self.subTest(field=field):
                original = copy.deepcopy(self.packet)
                self.packet['repair'][field] = 'tampered'
                result, calls = self.run_validation()
                self.assertEqual(result['status'], 'rejected')
                self.assertEqual(calls, 0)
                self.packet = original
        self.source.write_text(SOURCE + '# concurrent edit\n')
        result, calls = self.run_validation()
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(calls, 0)

    def test_new_or_strengthened_findings_rejected(self):
        after = copy.deepcopy(AFTER)
        other = copy.deepcopy(BEFORE['runs'][0]['results'][0])
        other['ruleId'] = 'zizmor/custom-check'
        location = other['locations'][0]['physicalLocation']
        location['region'] = {'startLine': 1, 'snippet': {'text': 'name: Review title'}}
        after['runs'][0]['results'] = [other]
        result, _ = self.run_validation([BEFORE, after])
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['new_findings'], 1)
        before = copy.deepcopy(BEFORE)
        weaker = copy.deepcopy(other)
        weaker['level'] = 'warning'
        before['runs'][0]['results'].append(weaker)
        result, _ = self.run_validation([before, after])
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['new_findings'], 1)

    def test_line_shifts_and_duplicate_multiplicity_compared(self):
        before = copy.deepcopy(BEFORE)
        unchanged = copy.deepcopy(before['runs'][0]['results'][0])
        unchanged['ruleId'] = 'zizmor/custom-check'
        before['runs'][0]['results'].append(unchanged)
        after = copy.deepcopy(AFTER)
        shifted = copy.deepcopy(unchanged)
        shifted['locations'][0]['physicalLocation']['region'] = {
            'startLine': 14, 'snippet': {'text': 'printf \'%s\\n\' "$SENTINEL_INPUT"'}}
        after['runs'][0]['results'] = [shifted]
        result, _ = self.run_validation([before, after])
        self.assertEqual(result['status'], 'validated')
        self.assertEqual(result['new_findings'], 0)
        after['runs'][0]['results'].append(copy.deepcopy(shifted))
        result, _ = self.run_validation([before, after])
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(result['new_findings'], 1)

    def test_missing_baseline_target_and_retained_target_rejected(self):
        result, _ = self.run_validation([AFTER, AFTER])
        self.assertEqual(result['status'], 'rejected')
        self.assertFalse(result['target_removed'])
        retained = copy.deepcopy(BEFORE)
        retained['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region'] = {
            'startLine': 14, 'snippet': {'text': 'printf \'%s\\n\' "$SENTINEL_INPUT"'}}
        result, _ = self.run_validation([BEFORE, retained])
        self.assertEqual(result['status'], 'rejected')
        self.assertIn('remains', result['reason'])

    def test_malformed_sarif_and_scanner_failures_unavailable(self):
        documents = [{}, {'version': '2.1.0', 'runs': [{}]}, copy.deepcopy(BEFORE)]
        documents[-1]['runs'][0]['results'][0]['locations'] = []
        for doc in documents:
            result, calls = self.run_validation([doc])
            self.assertEqual(result['status'], 'unavailable')
            self.assertEqual(calls, 1)
        for reason in ['Scanner timed out', 'Scanner exited with a failure status',
                       'Scanner output exceeded byte limit']:
            result, _ = self.run_validation([ScannerUnavailable(reason)])
            self.assertEqual(result['status'], 'unavailable')
            self.assertEqual(result['reason'], reason)

    def test_versions_and_local_refs_unsupported(self):
        newer = copy.deepcopy(BEFORE)
        newer['runs'][0]['tool']['driver']['semanticVersion'] = '99.0.0'
        result, calls = self.run_validation([newer])
        self.assertEqual(result['status'], 'unsupported')
        self.assertEqual(calls, 1)
        self.source.write_text(SOURCE.replace('      - name:', '      - uses: ./private-action\n      - name:'))
        # A new proposal for the changed source cannot scan missing local actions.
        from workflow_sentinel.investigation import Workflow
        source = self.source.read_text()
        doc = copy.deepcopy(BEFORE)
        doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region'] = {
            'startLine': 13, 'snippet': {'text': 'printf \'%s\\n\' "${{ github.event.pull_request.title }}"'}}
        self.assertIsNotNone(Workflow.parse('.github/workflows/review.yml', source.encode()))
        self.packet = investigate(doc, self.root, preview_repairs=True)['packets'][0]
        result, calls = self.run_validation()
        self.assertEqual(result['status'], 'unsupported')
        self.assertEqual(calls, 0)

    def test_cli_report_schema_and_candidate_budget(self):
        doc = copy.deepcopy(BEFORE)
        doc['runs'][0]['results'] *= 3
        with patch('workflow_sentinel.validation.scanner_path', return_value=Path('/installed/zizmor')):
            with patch('workflow_sentinel.validation.scan', side_effect=[BEFORE, AFTER] * 2) as mock:
                report = investigate(doc, self.root, validate_repairs=True)
        validate_schema(report, json.loads((ROOT / 'schemas/report.schema.json').read_text()))
        self.assertEqual(mock.call_count, 4)
        statuses = [p['static_validation']['status'] for p in report['packets']]
        self.assertEqual(sorted(statuses), ['unavailable', 'validated', 'validated'])
        self.assertNotIn('static_validation', investigate(BEFORE, self.root)['packets'][0])

    def test_scanner_inside_repo_or_wrapper_not_executed(self):
        binary = self.root / 'zizmor'
        binary.write_bytes(b'\x7fELF')
        binary.chmod(0o700)
        with self.assertRaisesRegex(ScannerUnavailable, 'outside'):
            scanner_path(self.root, binary)
        with tempfile.TemporaryDirectory() as tmp:
            wrapper = Path(tmp) / 'zizmor'
            wrapper.write_text('#!/bin/sh\necho untrusted\n')
            wrapper.chmod(0o700)
            with self.assertRaisesRegex(ScannerUnavailable, 'wrappers'):
                scanner_path(self.root, wrapper)

    def test_multiple_runs_cannot_be_compared(self):
        doc = copy.deepcopy(BEFORE)
        doc['runs'] *= 2
        with self.assertRaises(ComparisonUnsupported):
            findings(doc, self.root, '.github/workflows/review.yml')

    def test_relative_and_traversing_uses_never_reach_scanner(self):
        for reference in ['./private@main', 'owner/repo/../../private@main', '../private@main']:
            source = SOURCE.replace('      - name:', '      - uses: ' + reference + '\n      - name:')
            self.source.write_text(source)
            doc = copy.deepcopy(BEFORE)
            doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region'] = {
                'startLine': 13,
                'snippet': {'text': 'printf \'%s\\n\' "${{ github.event.pull_request.title }}"'}}
            self.packet = investigate(doc, self.root, preview_repairs=True)['packets'][0]
            result, calls = self.run_validation()
            self.assertEqual(result['status'], 'unsupported')
            self.assertEqual(calls, 0)


class FakeProcess:
    """Pipe-backed subprocess stand-in: no fixture commands are executed."""
    def __init__(self, output=b'{}', error=b'', code=0):
        self.stdout = self.pipe(output)
        self.stderr = self.pipe(error)
        self.code = code
        self.finished = False
        self.pid = 12345

    @staticmethod
    def pipe(data):
        read_fd, write_fd = os.pipe()
        os.write(write_fd, data)
        os.close(write_fd)
        return os.fdopen(read_fd, 'rb')

    def poll(self):
        return self.code if self.finished else None

    def wait(self, timeout=None):
        self.finished = True
        return self.code


class ScannerRunnerTests(unittest.TestCase):
    def test_fixed_invocation_environment_and_success(self):
        process = FakeProcess()
        with tempfile.TemporaryDirectory() as tmp:
            with patch('workflow_sentinel.validation.subprocess.Popen', return_value=process) as popen:
                self.assertEqual(scan(Path('/installed/zizmor'), Path(tmp)), {})
                args, kwargs = popen.call_args
                self.assertEqual(args[0], ['/installed/zizmor', *SCANNER_ARGS])
                self.assertEqual(kwargs['cwd'], Path(tmp))
                self.assertEqual(kwargs['stdin'], -3)
                self.assertNotIn('shell', kwargs)
                self.assertTrue(kwargs['start_new_session'])
                self.assertNotIn('GH_TOKEN', kwargs['env'])
                self.assertEqual(kwargs['env']['HOME'], tmp)
                self.assertIn('--no-config', args[0])
                self.assertIn('--no-ignores', args[0])

    def test_timeout_kills_process_group(self):
        process = FakeProcess()
        with patch('workflow_sentinel.validation.subprocess.Popen', return_value=process):
            with patch('workflow_sentinel.validation.TIMEOUT_SECONDS', 0):
                with patch('workflow_sentinel.validation.os.killpg') as kill:
                    with self.assertRaisesRegex(ScannerUnavailable, 'timed out'):
                        scan(Path('/installed/zizmor'), Path('/tmp'))
                    kill.assert_called_once_with(process.pid, signal.SIGKILL)
        self.assertTrue(process.stdout.closed)

    def test_output_limits_invalid_json_and_exit_failure(self):
        for process, reason, limit in [(FakeProcess(b'not-json'), 'valid JSON', 100),
                                       (FakeProcess(b'x' * 100), 'byte limit', 10),
                                       (FakeProcess(code=1), 'failure status', 100)]:
            with patch('workflow_sentinel.validation.subprocess.Popen', return_value=process):
                with patch('workflow_sentinel.validation.MAX_STDOUT', limit):
                    with patch('workflow_sentinel.validation.os.killpg'):
                        with self.assertRaisesRegex(ScannerUnavailable, reason):
                            scan(Path('/installed/zizmor'), Path('/tmp'))

    def test_launch_failure(self):
        with patch('workflow_sentinel.validation.subprocess.Popen', side_effect=OSError):
            with self.assertRaisesRegex(ScannerUnavailable, 'failed to start'):
                scan(Path('/installed/zizmor'), Path('/tmp'))
