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
    SCANNER_ARGS,
    ComparisonUnsupported,
    ScannerUnavailable,
    findings,
    scan,
    scanner_path,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/repairable"
SOURCE = (FIXTURE / ".github/workflows/review.yml").read_text()
BEFORE = json.loads((FIXTURE / "findings.zizmor-1.30.1.sarif").read_text())
AFTER = json.loads((FIXTURE / "fixed.findings.zizmor-1.30.1.sarif").read_text())


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / ".github/workflows/review.yml"
        self.source.parent.mkdir(parents=True)
        self.source.write_text(SOURCE)
        self.packet = investigate(BEFORE, self.root, preview_repairs=True)["packets"][0]

    def run_validation(self, outputs=None):
        with patch(
            "workflow_sentinel.validation.scanner_path", return_value=Path("/installed/zizmor")
        ):
            with patch(
                "workflow_sentinel.validation.scan", side_effect=outputs or [BEFORE, AFTER]
            ) as mock:
                result = validate(self.packet, self.root, None)
                return result, mock.call_count

    def test_success_disposable_snapshots_and_original_unchanged(self):
        observed = []

        def scanner(executable, directory):
            observed.append(
                (executable, directory, (directory / ".github/workflows/review.yml").read_text())
            )
            self.assertEqual(sorted(p.name for p in directory.iterdir()), [".github"])
            return BEFORE if len(observed) == 1 else AFTER

        with patch(
            "workflow_sentinel.validation.scanner_path", return_value=Path("/installed/zizmor")
        ):
            with patch("workflow_sentinel.validation.scan", side_effect=scanner):
                result = validate(self.packet, self.root, None)
        self.assertEqual(result["status"], "validated")
        self.assertEqual(result["before_findings"], 1)
        self.assertEqual(result["after_findings"], 0)
        self.assertTrue(result["target_removed"])
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(self.source.read_text(), SOURCE)
        self.assertEqual(observed[0][2], SOURCE)
        self.assertEqual(observed[1][2], (FIXTURE / "expected-fixed.yml").read_text())
        self.assertTrue(all(not directory.exists() for _, directory, _ in observed))

    def test_cli_report_schema_and_candidate_budget(self):
        doc = copy.deepcopy(BEFORE)
        doc["runs"][0]["results"] *= 3
        with patch(
            "workflow_sentinel.validation.scanner_path", return_value=Path("/installed/zizmor")
        ):
            with patch(
                "workflow_sentinel.validation.scan", side_effect=[BEFORE, AFTER] * 2
            ) as mock:
                report = investigate(doc, self.root, validate_repairs=True)
        validate_schema(report, json.loads((ROOT / "schemas/report.schema.json").read_text()))
        self.assertEqual(mock.call_count, 4)
        statuses = [p["static_validation"]["status"] for p in report["packets"]]
        self.assertEqual(sorted(statuses), ["unavailable", "validated", "validated"])

    def test_scanner_inside_repo_not_executed(self):
        binary = self.root / "zizmor"
        binary.write_bytes(b"\x7fELF")
        binary.chmod(0o700)
        with self.assertRaisesRegex(ScannerUnavailable, "outside"):
            scanner_path(self.root, binary)

    def test_multiple_runs_cannot_be_compared(self):
        doc = copy.deepcopy(BEFORE)
        doc["runs"] *= 2
        with self.assertRaises(ComparisonUnsupported):
            findings(doc, self.root, ".github/workflows/review.yml")

    def test_tampered_diff_never_reaches_scanner(self):
        self.packet["repair"]["unified_diff"] = "tampered"
        result, calls = self.run_validation()
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(calls, 0)

    def test_new_finding_rejects_candidate(self):
        after = copy.deepcopy(AFTER)
        other = copy.deepcopy(BEFORE["runs"][0]["results"][0])
        other["ruleId"] = "zizmor/custom-check"
        other["locations"][0]["physicalLocation"]["region"] = {
            "startLine": 1,
            "snippet": {"text": "name: Review title"},
        }
        after["runs"][0]["results"] = [other]
        result, _ = self.run_validation([BEFORE, after])
        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["new_findings"], 1)


class FakeProcess:
    """Pipe-backed subprocess stand-in: no fixture commands are executed."""

    def __init__(self, output=b"{}", error=b"", code=0):
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
        return os.fdopen(read_fd, "rb")

    def poll(self):
        return self.code if self.finished else None

    def wait(self, timeout=None):
        self.finished = True
        return self.code


class ScannerRunnerTests(unittest.TestCase):
    def test_fixed_invocation_environment_and_success(self):
        process = FakeProcess()
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "workflow_sentinel.validation.subprocess.Popen", return_value=process
            ) as popen:
                self.assertEqual(scan(Path("/installed/zizmor"), Path(tmp)), {})
                args, kwargs = popen.call_args
                self.assertEqual(args[0], ["/installed/zizmor", *SCANNER_ARGS])
                self.assertEqual(kwargs["cwd"], Path(tmp))
                self.assertEqual(kwargs["stdin"], -3)
                self.assertNotIn("shell", kwargs)
                self.assertTrue(kwargs["start_new_session"])
                self.assertNotIn("GH_TOKEN", kwargs["env"])
                self.assertEqual(kwargs["env"]["HOME"], tmp)
                self.assertIn("--no-config", args[0])
                self.assertIn("--no-ignores", args[0])

    def test_timeout_kills_process_group(self):
        process = FakeProcess()
        with patch("workflow_sentinel.validation.subprocess.Popen", return_value=process):
            with patch("workflow_sentinel.validation.TIMEOUT_SECONDS", 0):
                with patch("workflow_sentinel.validation.os.killpg") as kill:
                    with self.assertRaisesRegex(ScannerUnavailable, "timed out"):
                        scan(Path("/installed/zizmor"), Path("/tmp"))
                    kill.assert_called_once_with(process.pid, signal.SIGKILL)
        self.assertTrue(process.stdout.closed)
