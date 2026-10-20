import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sentinel_evaluation", ROOT / "evaluation/run.py")
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class EvaluationTests(unittest.TestCase):
    def test_manifest_integrity_and_audited_split(self):
        manifest = evaluation.loaded_manifest()
        counts = {
            split: sum(evaluation.effective_split(c) == split for c in manifest["cases"])
            for split in ["development", "holdout-first-use", "regression-reused"]
        }
        self.assertEqual(
            counts, {"development": 18, "holdout-first-use": 15, "regression-reused": 5}
        )
        self.assertEqual(len({c["id"] for c in manifest["cases"]}), 38)
