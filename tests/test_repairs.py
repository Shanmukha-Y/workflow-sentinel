import copy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from jsonschema import validate

from workflow_sentinel.cli import investigate
from workflow_sentinel.investigation import Workflow
from workflow_sentinel.repairs import RepairError, transform, tree

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures/repairable"
SOURCE = (FIXTURE / ".github/workflows/review.yml").read_text()
SARIF = json.loads((FIXTURE / "findings.zizmor-1.30.1.sarif").read_text())


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / ".github/workflows/review.yml"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(SOURCE)

    def report(self, source=SOURCE, sarif=None):
        self.path.write_text(source)
        doc = copy.deepcopy(sarif or SARIF)
        if sarif is None:
            workflow = Workflow.parse(".github/workflows/review.yml", source.encode())
            route, node = next(
                (route, node)
                for route, node in workflow.entries
                if route == ("jobs", "review", "steps", 0, "run")
                and getattr(node, "style", None) == "|"
            )
            region = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
            region.clear()
            region.update({"startLine": node.start_mark.line + 2, "snippet": {"text": node.value}})
        result = investigate(doc, self.root, preview_repairs=True)
        validate(result, json.loads((ROOT / "schemas/report.schema.json").read_text()))
        return result

    def test_real_sarif_preview_is_valid_and_source_unchanged(self):
        before = self.path.read_bytes()
        packet = self.report(sarif=SARIF)["packets"][0]
        repair = packet["repair"]
        self.assertEqual(repair["status"], "proposed")
        self.assertEqual(repair["base_sha256"], hashlib.sha256(before).hexdigest())
        self.assertIn("+          SENTINEL_INPUT:", repair["unified_diff"])
        self.assertIn("+          printf", repair["unified_diff"])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.report(sarif=SARIF)["packets"][0]["repair"], repair)
        # Apply diff only as data to this disposable fixture, never execute its run block.
        process = subprocess.run(
            ["git", "apply", "--check", "-"],
            input=repair["unified_diff"],
            text=True,
            cwd=self.root,
            capture_output=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        process = subprocess.run(
            ["git", "apply", "-"],
            input=repair["unified_diff"],
            text=True,
            cwd=self.root,
            capture_output=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(
            hashlib.sha256(self.path.read_bytes()).hexdigest(), repair["proposed_sha256"]
        )
        self.assertEqual(self.path.read_text(), (FIXTURE / "expected-fixed.yml").read_text())
        value = tree(Workflow.parse(".github/workflows/review.yml", self.path.read_bytes()).root)
        step = value["jobs"]["review"]["steps"][0]
        self.assertEqual(step["run"], "printf '%s\\n' \"$SENTINEL_INPUT\"\n")
        self.assertEqual(step["env"], {"SENTINEL_INPUT": "${{ github.event.pull_request.title }}"})

    def test_format_without_newline_preserves_intended_literal_argument(self):
        source = SOURCE.replace("'%s\\n'", "'%s'")
        packet = self.report(source)["packets"][0]
        self.assertEqual(packet["repair"]["status"], "proposed")
        proposed = transform(
            Workflow.parse(".github/workflows/review.yml", source.encode()), packet["evidence"][0]
        )
        step = tree(Workflow.parse(".github/workflows/review.yml", proposed.encode()).root)["jobs"][
            "review"
        ]["steps"][0]
        self.assertEqual(step["run"], "printf '%s' \"$SENTINEL_INPUT\"\n")
        # Structural checks preserve the fixed printf format and pass the expression as one
        # quoted parameter. Runtime behavior is deliberately not tested by executing the script.
        self.assertEqual(step["env"]["SENTINEL_INPUT"], "${{ github.event.pull_request.title }}")

    def test_quoted_and_flow_run_forms_refuse(self):
        source = SOURCE.replace(
            "        run: |\n          printf '%s\\n' \"${{ github.event.pull_request.title }}\"\n",
            '        run: "printf literal"\n',
        )
        doc = copy.deepcopy(SARIF)
        region = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["region"]
        region.clear()
        region.update({"startLine": 11, "snippet": {"text": "printf literal"}})
        packet = self.report(source, doc)["packets"][0]
        self.assertEqual(packet["decision"], "review")
        self.assertIn("literal run", packet["repair"]["reason"])

    def test_repair_rejects_unconventional_path(self):
        packet = self.report(sarif=SARIF)["packets"][0]
        workflow = Workflow.parse("other.yml", SOURCE.encode())
        with self.assertRaisesRegex(RepairError, "conventional"):
            transform(workflow, packet["evidence"][0])

    def test_shell_redirection_refuses(self):
        source = SOURCE.replace('}}"', '}}" > output')
        packet = self.report(source)["packets"][0]
        self.assertEqual(packet["repair"]["status"], "abstain")
        self.assertIsNone(packet["repair"]["unified_diff"])

    def test_existing_step_environment_refuses(self):
        source = SOURCE.replace("        shell: bash", "        shell: bash\n        env: {}")
        self.assertEqual(self.report(source)["packets"][0]["repair"]["status"], "abstain")

    def test_dangerous_checkout_remains_report_only(self):
        doc = copy.deepcopy(SARIF)
        doc["runs"][0]["results"][0]["ruleId"] = "zizmor/dangerous-triggers"
        repair = self.report(sarif=doc)["packets"][0]["repair"]
        self.assertEqual(repair["status"], "abstain")
        self.assertIsNone(repair["unified_diff"])
