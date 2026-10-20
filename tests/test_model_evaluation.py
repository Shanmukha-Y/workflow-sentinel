"""Model harness scoring/budget regressions; no live API calls."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


from workflow_sentinel.agent import _execute as run
from workflow_sentinel.model_evaluation import (
    evaluate as execute_evaluation,
    evaluate_to_file as execute_to_file,
    manifest,
    score,
)


def evaluate(*args, **kwargs):
    return execute_evaluation(*args, **{"mode": "mock", **kwargs})


def evaluate_to_file(*args, **kwargs):
    return execute_to_file(*args, **{"mode": "mock", **kwargs})


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "model_evaluation/manifest.json"
SPEC = importlib.util.spec_from_file_location(
    "model_mock", ROOT / "tests/helpers/model_transport.py"
)
MOCK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOCK)


def fake_scan(packet, root, scanner):
    return {"status": "validated", "target_removed": True, "new_findings": 0, "attempts": 2}


class ModelEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.doc = manifest(MANIFEST)

    def report(self, case, script):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            p = repo / self.doc["path"]
            p.parent.mkdir(parents=True)
            p.write_text(case["source"])
            with patch("workflow_sentinel.agent.validate", side_effect=fake_scan):
                return run(case["sarif"], repo, script, Path("/mock/zizmor"))

    def test_adapter_error_is_not_correct_abstention(self):
        case = self.doc["cases"][5]
        report = self.report(case, [{"action": "abstain"}])
        report["trace"] = [{"turn": 0, "status": "adapter-error"}]
        self.assertFalse(score(case, report, True)["passed"])

    def test_early_finish_not_useful_repair_or_manual_review(self):
        case = self.doc["cases"][0]
        report = self.report(
            case, [{"action": "evidence", "packet": 0}, {"action": "finish", "packet": 0}]
        )
        self.assertFalse(score(case, report, True)["passed"])
