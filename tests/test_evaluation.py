import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('sentinel_evaluation', ROOT / 'evaluation/run.py')
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class EvaluationTests(unittest.TestCase):
    def test_manifest_integrity_and_audited_split(self):
        manifest = evaluation.loaded_manifest()
        counts = {split: sum(evaluation.effective_split(c) == split for c in manifest['cases'])
                  for split in ['development', 'holdout-first-use', 'regression-reused']}
        self.assertEqual(counts, {'development': 18, 'holdout-first-use': 15, 'regression-reused': 5})
        self.assertEqual(len({c['id'] for c in manifest['cases']}), 38)
        with patch.object(evaluation, 'digest', return_value='tampered'):
            with self.assertRaisesRegex(ValueError, 'frozen labels'):
                evaluation.loaded_manifest()

    def test_original_records_and_production_hashes_preserved(self):
        for name in ['first-run-development', 'first-run-holdout']:
            report = json.loads((ROOT / f'evaluation/results/{name}.json').read_text())
            self.assertEqual(report['run_kind'], 'first-use')
            history = json.loads((ROOT / 'evaluation/HISTORY.json').read_text())
            self.assertEqual(hashlib.sha256((ROOT / f'evaluation/results/{name}.json')
                                           .read_bytes()).hexdigest(),
                             history['immutable_first_run_records_sha256'][name + '.json'])
            self.assertEqual(report['production_baseline_commit'],
                             evaluation.loaded_manifest()['frozen_against_commit'])
            self.assertFalse(any(row['failures'] for row in report['cases']))
        # Original attribution mistake remains visible, rather than overwritten with a rerun.
        raw = json.loads((ROOT / 'evaluation/results/first-run-holdout.json').read_text())
        dynamic = next(c for c in raw['cases'] if c['id'] == 'holdout-dynamic-action')
        self.assertEqual(dynamic['validation_detail']['attempts'], 0)
        self.assertEqual(dynamic['validation_mode'], 'live-scanner')
        audited = json.loads((ROOT / 'evaluation/results/first-run-audited-summary.json').read_text())
        self.assertEqual(audited['subsets']['holdout-first-use']['live_validation_label_agreement'],
                         {'numerator': 4, 'denominator': 4, 'value': 1.0})

    def test_offline_evaluation_never_invokes_scanner(self):
        manifest = evaluation.loaded_manifest()
        case = next(c for c in manifest['cases'] if c['id'] == 'dev-printf-title')
        with patch('workflow_sentinel.validation.scan') as scanner:
            result = evaluation.evaluate_case(case, manifest['path'], None)
        scanner.assert_not_called()
        self.assertEqual(result['validation'], 'not-run')
        self.assertTrue(result['repair_exact'])
        self.assertTrue(result['source_unchanged'])

    def test_unexpected_outcomes_fail_and_zero_denominators_are_not_perfect_scores(self):
        manifest = evaluation.loaded_manifest()
        case = copy.deepcopy(next(c for c in manifest['cases'] if c['id'] == 'dev-printf-title'))
        case['expected']['repair'] = 'abstain'
        case['expected'].pop('candidate_source')
        result = evaluation.evaluate_case(case, manifest['path'], None)
        self.assertFalse(result['passed_observed_checks'])
        self.assertIn('Diff does not produce the independently labeled candidate', result['failures'])
        self.assertEqual(evaluation.metrics([result])['repair_eligibility_precision']['value'], 0)
        self.assertIsNone(evaluation.metrics([])['live_validation_label_agreement']['value'])
