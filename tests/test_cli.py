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
        for name, doc in [("report", report), ("input", self.sarif)]:
            validate(doc, json.loads((ROOT / f"schemas/{name}.schema.json").read_text()))

    def test_safe(self):
        doc = json.loads((ROOT / "fixtures/safe/findings.sarif").read_text())
        self.assertEqual(investigate(doc, ROOT / "fixtures/safe")["packets"], [])

    def test_abstentions(self):
        for uri in ["../outside.yml", "%2e%2e/outside.yml", "/tmp/x.yml",
                    "https://example.com/x.yml", "file:///tmp/x.yml", "missing.yml"]:
            doc = copy.deepcopy(self.sarif)
            doc["runs"][0]["results"] = [doc["runs"][0]["results"][0]]
            loc = doc["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
            loc["artifactLocation"]["uri"] = uri
            self.assertEqual(investigate(doc, FIXTURE)["packets"][0]["decision"], "abstain")
        for item in [{"ruleId": "unknown"}, {"ruleId": "template-injection"}]:
            doc["runs"][0]["results"] = [item]
            self.assertEqual(investigate(doc, FIXTURE)["packets"][0]["decision"], "abstain")

    def test_stale_line(self):
        self.sarif["runs"][0]["results"] = [self.sarif["runs"][0]["results"][0]]
        loc = self.sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]
        loc["region"]["startLine"] = 999
        self.assertEqual(investigate(self.sarif, FIXTURE)["packets"][0]["decision"], "abstain")

    def test_symlink_and_size(self):
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
            (root / "large").write_bytes(b"x" * (MAX_BYTES + 1))
            with self.assertRaises(ValueError):
                read_bounded(root / "large")

    def test_invalid_and_cli(self):
        with self.assertRaises(ValueError):
            investigate({"version": "bad"}, FIXTURE)
        proc = subprocess.run([sys.executable, "-m", "workflow_sentinel.cli", "--sarif",
                               str(FIXTURE / "findings.sarif"), "--repo", str(FIXTURE)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(json.loads(proc.stdout)["mode"], "offline-deterministic")

    def test_malformed_locations_abstain(self):
        self.sarif['runs'][0]['results'] = [self.sarif['runs'][0]['results'][0]]
        for location in [None, [], {'physicalLocation': {'artifactLocation': []}}]:
            self.sarif['runs'][0]['results'][0]['locations'] = [location]
            report = investigate(self.sarif, FIXTURE)
            self.assertEqual(report['packets'][0]['decision'], 'abstain')

    def test_malformed_documents(self):
        for doc in [[], {'version': '2.1.0', 'runs': [None]},
                    {'version': '2.1.0', 'runs': [{'tool': {'driver': None}}]}]:
            with self.assertRaises(ValueError):
                investigate(doc, FIXTURE)

    def test_result_limit(self):
        self.sarif['runs'][0]['results'] = [{'ruleId': 'unknown'}] * 1001
        with self.assertRaises(ValueError):
            investigate(self.sarif, FIXTURE)

    def test_supported_prefixes_match_legacy_reports(self):
        prefixed = copy.deepcopy(self.sarif)
        for result in prefixed['runs'][0]['results']:
            result['ruleId'] = 'zizmor/' + result['ruleId']
        original = copy.deepcopy(prefixed)
        self.assertEqual(investigate(prefixed, FIXTURE), investigate(self.sarif, FIXTURE))
        self.assertEqual(prefixed, original)

    def test_unknown_and_lookalike_prefixes_still_abstain(self):
        for rule in ['zizmor/unknown', 'zizmor/unpinned-uses', 'other/template-injection',
                     'ZIZMOR/template-injection', 'zizmor/zizmor/template-injection',
                     'zizmor/template-injection/extra', 'zizmor/']:
            doc = copy.deepcopy(self.sarif)
            result = doc['runs'][0]['results'][0]
            result['ruleId'] = rule
            doc['runs'][0]['results'] = [result]
            packet = investigate(doc, FIXTURE)['packets'][0]
            self.assertEqual(packet['rule_id'], rule)
            self.assertEqual(packet['decision'], 'abstain')
            self.assertEqual(packet['reason'], 'Unsupported rule')
            self.assertEqual(packet['evidence'], [])

    def test_prefixed_rule_requires_valid_local_evidence(self):
        result = self.sarif['runs'][0]['results'][0]
        result['ruleId'] = 'zizmor/template-injection'
        self.sarif['runs'][0]['results'] = [result]
        result['locations'][0]['physicalLocation']['artifactLocation']['uri'] = '../x.yml'
        packet = investigate(self.sarif, FIXTURE)['packets'][0]
        self.assertEqual(packet['decision'], 'abstain')
        self.assertTrue(packet['reason'].startswith('Insufficient local evidence:'))

    def test_captured_zizmor_1_30_1_sarif(self):
        doc = json.loads((FIXTURE / 'findings.zizmor-1.30.1.sarif').read_text())
        self.assertEqual(doc['runs'][0]['tool']['driver']['semanticVersion'], '1.30.1')
        report = investigate(doc, FIXTURE)
        packets = {p['rule_id']: p for p in report['packets']}
        self.assertEqual({rule: p['decision'] for rule, p in packets.items()}, {
            'template-injection': 'review', 'dangerous-triggers': 'review',
            'excessive-permissions': 'review', 'zizmor/artipacked': 'abstain',
            'zizmor/unpinned-uses': 'abstain', 'zizmor/anonymous-definition': 'abstain',
            'zizmor/concurrency-limits': 'abstain',
        })
        self.assertEqual(packets['template-injection']['evidence'][0]['line'], 11)
        self.assertEqual(packets['excessive-permissions']['evidence'][0]['line'], 3)
        self.assertIn('pull_request.title',
                      packets['template-injection']['evidence'][0]['excerpt'])
        self.assertIn('https://docs.zizmor.sh/audits/#template-injection',
                      packets['template-injection']['citations'])
        for name, value in [('input', doc), ('report', report)]:
            validate(value, json.loads((ROOT / f'schemas/{name}.schema.json').read_text()))
        process = subprocess.run([sys.executable, '-m', 'workflow_sentinel.cli', '--sarif',
                                  str(FIXTURE / 'findings.zizmor-1.30.1.sarif'), '--repo',
                                  str(FIXTURE)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(json.loads(process.stdout), report)
