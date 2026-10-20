import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import validate

from workflow_sentinel.cli import investigate
from workflow_sentinel.investigation import RepositoryReader

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = """on: [pull_request_target, workflow_dispatch]
permissions: write-all
jobs:
  check:
    permissions: {}
    if: github.actor != 'dependabot[bot]'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - env:
          TITLE: ${{ github.event.pull_request.title }}
        run: |
          echo "${{ github.event.pull_request.title }}"
          printf '%s' "$TITLE"
        shell: bash
        if: github.event_name == 'pull_request_target'
"""


def document(line=15, column=None, snippet=None):
    region = {"startLine": line}
    if column is not None:
        region["startColumn"] = column
    if snippet is not None:
        region["snippet"] = {"text": snippet}
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "zizmor"}},
                "results": [
                    {
                        "ruleId": "zizmor/template-injection",
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "workflow.yml"},
                                    "region": region,
                                }
                            }
                        ],
                    }
                ],
            }
        ],
    }


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "workflow.yml").write_text(WORKFLOW)

    def report(self, doc=None, text=None):
        if text is not None:
            (self.root / "workflow.yml").write_text(text)
        report = investigate(doc or document(), self.root)
        validate(report, json.loads((ROOT / "schemas/report.schema.json").read_text()))
        return report["packets"][0]

    def test_multiline_context_permissions_env_and_precise_citations(self):
        packet = self.report(document(column=11))
        self.assertEqual(packet["decision"], "review")
        evidence = packet["evidence"][0]
        self.assertEqual(evidence["yaml_path"], ["jobs", "check", "steps", 1, "run"])
        self.assertEqual(evidence["citation"], "workflow.yml:15:11-15:56")
        context = evidence["context"]
        self.assertEqual(context["triggers"], ["pull_request_target", "workflow_dispatch"])
        self.assertEqual(context["permissions"], {"source": "job", "declaration": {}})
        self.assertEqual(context["job"], "check")
        self.assertEqual(context["step_index"], 1)
        self.assertEqual(context["shell"], "bash")
        self.assertEqual(context["run_expressions"], ["github.event.pull_request.title"])
        self.assertEqual(context["env_expressions"], {"TITLE": ["github.event.pull_request.title"]})
        self.assertEqual(
            context["checkouts"][0]["ref"], "${{ github.event.pull_request.head.sha }}"
        )
        self.assertTrue(any(c.startswith("workflow.yml:5:") for c in context["citations"]))
        self.assertEqual(evidence["provenance"], "unverified")
        self.assertTrue(any(t.startswith("context:") for t in packet["trace"]))

    def test_workflow_scope_includes_checkout_across_jobs(self):
        packet = self.report(document(line=1, column=1))
        context = packet["evidence"][0]["context"]
        self.assertEqual(context["job"], None)
        self.assertEqual(context["permissions"]["source"], "workflow")
        self.assertEqual(context["checkouts"][0]["job"], "check")

    def test_stale_snippet_abstains(self):
        packet = self.report(document(snippet="old source"))
        self.assertEqual(packet["decision"], "abstain")
        self.assertIn("source snippet mismatch", packet["reason"])
        self.assertEqual(packet["evidence"], [])

    def test_repeated_locations_share_one_snapshot(self):
        doc = document()
        result = doc["runs"][0]["results"][0]
        doc["runs"][0]["results"].append(copy.deepcopy(result))
        original = RepositoryReader.read
        calls = []

        def counted(reader, path):
            calls.append(path)
            return original(reader, path)

        with patch.object(RepositoryReader, "read", counted):
            report = investigate(doc, self.root)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report["packets"][0], report["packets"][1])

    def test_hash_metadata_uses_normalized_relative_path(self):
        doc = document()
        doc["runs"][0]["artifacts"] = [
            {"location": {"uri": "./workflow.yml"}, "hashes": {"sha-256": "0" * 64}}
        ]
        self.assertIn("source hash mismatch", self.report(doc)["reason"])

    def test_failed_reads_consume_file_budget(self):
        reader = RepositoryReader(self.root)
        with patch("workflow_sentinel.investigation.MAX_FILES", 1):
            with self.assertRaises(OSError):
                reader.read(Path("missing.yml"))
            with self.assertRaisesRegex(ValueError, "file budget"):
                reader.read(Path("workflow.yml"))

    def test_duplicate_yaml_keys_abstain(self):
        self.assertEqual(
            self.report(document(line=1), WORKFLOW + "jobs: {}\n")["decision"], "abstain"
        )

    def test_yaml_depth_budget(self):
        text = "on: push\njobs: " + "[" * 33 + "x" + "]" * 33
        self.assertIn("depth budget", self.report(document(line=1), text)["reason"])
