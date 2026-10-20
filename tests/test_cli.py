import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from jsonschema import validate
from workflow_sentinel.cli import MAX_BYTES, investigate, read_bounded

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/vulnerable"


class SentinelTests(unittest.TestCase):
    def setUp(self):
        self.sarif = json.loads((FIXTURE / "findings.sarif").read_text())

    def test_deterministic_and_schema(self):
        report = investigate(self.sarif, FIXTURE)
        self.assertEqual(report, investigate(self.sarif, FIXTURE))
        self.assertEqual(len(report["packets"]), 3)
        self.assertTrue(all(p["decision"] == "review" for p in report["packets"]))
        validate(report, json.loads((ROOT / "schemas/report.schema.json").read_text()))

    def test_safe(self):
        doc = json.loads((ROOT / "fixtures/safe/findings.sarif").read_text())
        self.assertEqual(investigate(doc, ROOT / "fixtures/safe")["packets"], [])

    def test_stale_line(self):
        self.sarif["runs"][0]["results"] = [self.sarif["runs"][0]["results"][0]]
        loc = self.sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        loc["region"]["startLine"] = 999
        self.assertEqual(investigate(self.sarif, FIXTURE)["packets"][0]["decision"], "abstain")

    def test_symlink_abstains(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "repo").mkdir()
            (root / "outside.yml").write_text("secret")
            (root / "repo/link.yml").symlink_to(root / "outside.yml")
            self.sarif["runs"][0]["results"] = [self.sarif["runs"][0]["results"][0]]
            loc = self.sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
            loc["artifactLocation"]["uri"] = "link.yml"
            report = investigate(self.sarif, root / "repo")
            self.assertEqual(report["packets"][0]["decision"], "abstain")

    def test_offline_cli(self):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "workflow_sentinel.cli",
                "--sarif",
                str(FIXTURE / "findings.sarif"),
                "--repo",
                str(FIXTURE),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["mode"], "offline-deterministic")

    def test_result_limit(self):
        self.sarif["runs"][0]["results"] = [{"ruleId": "unknown"}] * 1001
        with self.assertRaises(ValueError):
            investigate(self.sarif, FIXTURE)

    def test_encoded_traversal_abstains(self):
        doc = copy.deepcopy(self.sarif)
        doc["runs"][0]["results"] = [doc["runs"][0]["results"][0]]
        location = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        location["artifactLocation"]["uri"] = "%2e%2e/outside.yml"
        self.assertEqual(investigate(doc, FIXTURE)["packets"][0]["decision"], "abstain")

    def test_oversize_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "large"
            path.write_bytes(b"x" * (MAX_BYTES + 1))
            with self.assertRaises(ValueError):
                read_bounded(path)
