"""Adversarial structured adapter tests; these do not measure model quality."""

import copy
import json
from pathlib import Path
import unittest

from unittest.mock import patch

from workflow_sentinel.agent import decode, request, _execute as run

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "fixtures/repairable"
SARIF = json.loads((REPO / "findings.zizmor-1.30.1.sarif").read_text())


def cmd(action, packet=0):
    return {"action": action, "packet": packet}


class AgentTests(unittest.TestCase):
    def test_validated_proposal_and_source_unchanged(self):
        before = {p: p.read_bytes() for p in REPO.rglob("*") if p.is_file()}
        with patch(
            "workflow_sentinel.agent.validate", return_value={"status": "validated"}
        ) as mock:
            result = run(
                SARIF,
                REPO,
                [cmd("evidence"), cmd("propose"), cmd("validate"), cmd("finish")],
                Path("/installed/zizmor"),
            )
        self.assertEqual(result["decision"], "review")
        mock.assert_called_once()
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_trace_excludes_adversarial_output(self):
        secret = "INSTRUCTION_TOKEN_do_not_store"
        result = run(SARIF, REPO, [{"action": secret, "credentials": secret}])
        self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(result["trace"], [{"turn": 0, "status": "invalid-response"}])

    def test_bad_evidence_cannot_be_overridden(self):
        sarif = copy.deepcopy(SARIF)
        sarif["runs"][0]["results"][0]["ruleId"] = "unsupported-rule"
        result = run(sarif, REPO, [cmd("evidence"), cmd("propose"), cmd("finish")])
        self.assertEqual(result["decision"], "abstain")
        self.assertEqual(result["report"]["packets"][0]["repair"]["status"], "abstain")

    def test_duplicate_json_fields(self):
        with self.assertRaises(ValueError):
            decode(b'[{"action":"shell","action":"abstain"}]')

    def test_unvalidated_completion_abstains(self):
        with patch("workflow_sentinel.agent.validate", side_effect=AssertionError("must not call")):
            result = run(SARIF, REPO, [cmd("evidence"), cmd("propose"), cmd("finish")])
        self.assertEqual(result["decision"], "abstain")

    def test_arbitrary_shell_tool_rejected(self):
        with self.assertRaises(ValueError):
            request({"action": "shell", "command": "id"}, 1)
