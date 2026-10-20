"""Integrity and bookkeeping checks against retained actual inference, no new model calls."""

import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "comparison_summary", ROOT / "comparison/summarize.py"
)
SUMMARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY)


class ComparisonRecordTests(unittest.TestCase):
    def test_frozen_final_setup_and_complete_actual_trials(self):
        protocol = json.loads((ROOT / "comparison/PROTOCOL.json").read_text())
        for name, expected in protocol["frozen_sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)
        index = json.loads((ROOT / "comparison/results/index.json").read_text())
        self.assertEqual(len(index["rows"]), 12)
        self.assertEqual(index["reserved_requests"], 251)
        cases = 0
        for row in index["rows"]:
            report = json.loads((ROOT / "comparison/results" / row["file"]).read_text())
            self.assertEqual(report["mode"], "local")
            self.assertTrue(report["capture_raw_evidence"])
            for case in report["cases"]:
                cases += 1
                self.assertTrue(case["source_unchanged"])
                self.assertEqual(case["observed_gate_breaches"], 0)
                for attempt in case["attempts"]:
                    self.assertEqual(attempt["raw_request"]["model"], report["model"])
                    self.assertEqual(attempt["raw_response"]["model"], report["model"])
                    self.assertEqual(attempt["raw_request"]["options"]["num_predict"], 256)
        self.assertEqual(cases, 90)

    def test_derived_summary_and_failures_are_not_removed(self):
        current = SUMMARY.summarize(ROOT / "comparison/results")
        saved = json.loads((ROOT / "comparison/SUMMARY.json").read_text())
        self.assertEqual(current, saved)
        mistral = next(m for m in current["models"] if m["model"].startswith("mistral"))
        self.assertEqual(mistral["all_cases"], {"successes": 20, "cases": 30})
        self.assertEqual(mistral["invalid_tool_attempts"], 10)
        self.assertEqual(mistral["disallowed_tool_attempts"], 0)
        self.assertEqual(mistral["fresh_by_category"]["benign-control"]["successes"], 0)
        self.assertEqual(mistral["fresh_by_category"]["evidence-control"]["successes"], 0)
        self.assertEqual(mistral["fresh_by_category"]["supported-repair"]["successes"], 4)
