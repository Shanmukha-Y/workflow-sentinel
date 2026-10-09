import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from jsonschema import validate

from workflow_sentinel.cli import investigate
from workflow_sentinel.investigation import Workflow
from workflow_sentinel.repairs import RepairError, transform, tree

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'fixtures/repairable'
SOURCE = (FIXTURE / '.github/workflows/review.yml').read_text()
SARIF = json.loads((FIXTURE / 'findings.zizmor-1.30.1.sarif').read_text())


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / '.github/workflows/review.yml'
        self.path.parent.mkdir(parents=True)
        self.path.write_text(SOURCE)

    def report(self, source=SOURCE, sarif=None):
        self.path.write_text(source)
        doc = copy.deepcopy(sarif or SARIF)
        if sarif is None:
            workflow = Workflow.parse('.github/workflows/review.yml', source.encode())
            route, node = next((route, node) for route, node in workflow.entries
                               if route == ('jobs', 'review', 'steps', 0, 'run')
                               and getattr(node, 'style', None) == '|')
            region = doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region']
            region.clear()
            region.update({'startLine': node.start_mark.line + 2,
                           'snippet': {'text': node.value}})
        result = investigate(doc, self.root, preview_repairs=True)
        validate(result, json.loads((ROOT / 'schemas/report.schema.json').read_text()))
        return result

    def test_real_sarif_preview_is_valid_and_source_unchanged(self):
        before = self.path.read_bytes()
        packet = self.report(sarif=SARIF)['packets'][0]
        repair = packet['repair']
        self.assertEqual(repair['status'], 'proposed')
        self.assertEqual(repair['base_sha256'], hashlib.sha256(before).hexdigest())
        self.assertIn('+          SENTINEL_INPUT:', repair['unified_diff'])
        self.assertIn('+          printf', repair['unified_diff'])
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.report(sarif=SARIF)['packets'][0]['repair'], repair)
        # Apply diff only as data to this disposable fixture, never execute its run block.
        process = subprocess.run(['git', 'apply', '--check', '-'], input=repair['unified_diff'],
                                 text=True, cwd=self.root, capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        process = subprocess.run(['git', 'apply', '-'], input=repair['unified_diff'],
                                 text=True, cwd=self.root, capture_output=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(),
                         repair['proposed_sha256'])
        self.assertEqual(self.path.read_text(), (FIXTURE / 'expected-fixed.yml').read_text())
        value = tree(Workflow.parse('.github/workflows/review.yml', self.path.read_bytes()).root)
        step = value['jobs']['review']['steps'][0]
        self.assertEqual(step['run'], 'printf \'%s\\n\' "$SENTINEL_INPUT"\n')
        self.assertEqual(step['env'], {'SENTINEL_INPUT': '${{ github.event.pull_request.title }}'})

    def test_unsafe_and_ambiguous_scripts_refuse(self):
        original = 'printf \'%s\\n\' "${{ github.event.pull_request.title }}"'
        scripts = [
            'echo "${{ github.event.pull_request.title }}"',
            'eval "${{ github.event.pull_request.title }}"',
            'printf \'%s\\n\' "${{ github.event.pull_request.title }}"; other',
            'printf \'%s\\n\' "${{ github.event.pull_request.title }}" > output',
            'printf \'%s\\n\' "$(echo ${{ github.event.pull_request.title }})"',
            'printf \'%s\\n\' "${{ github.event.pull_request.title }}${{ github.head_ref }}"',
            'printf \'%s\\n\' "${{ secrets.TOKEN }}"',
            'printf \'%s\\n\' "${{ github.event.pull_request.title || github.head_ref }}"',
            'printf \'%s\\n\' "${{ github.event.pull_request.title }}"\n          other',
        ]
        for script in scripts:
            with self.subTest(script=script):
                packet = self.report(SOURCE.replace(original, script))['packets'][0]
                self.assertEqual(packet['repair']['status'], 'abstain')
                self.assertEqual(packet['repair']['unified_diff'], None)

    def test_execution_and_environment_ambiguity_refuse(self):
        sources = [SOURCE.replace('shell: bash', 'shell: sh'),
                   SOURCE.replace('        shell: bash\n', ''),
                   SOURCE.replace('        shell: bash', '        shell: bash\n        env: {}'),
                   SOURCE.replace('jobs:', 'env: {}\njobs:'),
                   SOURCE.replace('    runs-on:', '    env: {}\n    runs-on:'),
                   SOURCE.replace('    runs-on:', '    container: ubuntu\n    runs-on:'),
                   SOURCE.replace('jobs:', 'defaults: {}\njobs:'),
                   SOURCE.replace('        run: |', '        run: |-'),
                   SOURCE.replace('        run: |', '        run: | # comment'),
                   SOURCE.replace('name: Review title', 'name: SENTINEL_INPUT'),
                   SOURCE.replace('\n', '\r\n'), SOURCE.rstrip('\n')]
        for source in sources:
            with self.subTest(source=source[:40]):
                packet = self.report(source)['packets'][0]
                self.assertEqual(packet['repair']['status'], 'abstain')

    def test_stale_unverified_and_multiple_locations_refuse(self):
        doc = copy.deepcopy(SARIF)
        region = doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region']
        del region['snippet']
        self.assertIn('requires a matching',
                      self.report(sarif=doc)['packets'][0]['repair']['reason'])
        doc = copy.deepcopy(SARIF)
        doc['runs'][0]['results'][0]['locations'] *= 2
        self.assertIn('exactly one', self.report(sarif=doc)['packets'][0]['repair']['reason'])
        source = SOURCE.replace('pull_request.title', 'pull_request.body')
        packet = self.report(source, SARIF)['packets'][0]
        self.assertEqual(packet['decision'], 'abstain')
        self.assertEqual(packet['repair']['status'], 'abstain')

    def test_already_fixed_script_never_proposes_again(self):
        packet = self.report(sarif=SARIF)['packets'][0]
        workflow = Workflow.parse('.github/workflows/review.yml', SOURCE.encode())
        fixed = transform(workflow, packet['evidence'][0])
        self.assertEqual(self.report(fixed, SARIF)['packets'][0]['repair']['status'], 'abstain')
        empty = copy.deepcopy(SARIF)
        empty['runs'][0]['results'] = []
        self.assertEqual(self.report(fixed, empty)['packets'], [])

    def test_permission_and_checkout_remain_report_only(self):
        for rule in ['zizmor/excessive-permissions', 'zizmor/dangerous-triggers']:
            doc = copy.deepcopy(SARIF)
            doc['runs'][0]['results'][0]['ruleId'] = rule
            packet = self.report(sarif=doc)['packets'][0]
            self.assertEqual(packet['repair']['status'], 'abstain')
            self.assertEqual(packet['repair']['unified_diff'], None)

    def test_format_without_newline_preserves_intended_literal_argument(self):
        source = SOURCE.replace("'%s\\n'", "'%s'")
        packet = self.report(source)['packets'][0]
        self.assertEqual(packet['repair']['status'], 'proposed')
        proposed = transform(Workflow.parse('.github/workflows/review.yml', source.encode()),
                             packet['evidence'][0])
        step = tree(Workflow.parse('.github/workflows/review.yml', proposed.encode()).root)[
            'jobs']['review']['steps'][0]
        self.assertEqual(step['run'], 'printf \'%s\' "$SENTINEL_INPUT"\n')
        # Structural checks preserve the fixed printf format and pass the expression as one
        # quoted parameter. Runtime behavior is deliberately not tested by executing the script.
        self.assertEqual(step['env']['SENTINEL_INPUT'], '${{ github.event.pull_request.title }}')

    def test_source_hash_guard_and_cli_opt_in(self):
        packet = self.report(sarif=SARIF)['packets'][0]
        evidence = copy.deepcopy(packet['evidence'][0])
        evidence['sha256'] = '0' * 64
        with self.assertRaisesRegex(RepairError, 'source snapshot'):
            transform(Workflow.parse('.github/workflows/review.yml', SOURCE.encode()), evidence)
        report = investigate(SARIF, self.root)
        self.assertNotIn('repair', report['packets'][0])
        process = subprocess.run([sys.executable, '-m', 'workflow_sentinel.cli', '--sarif',
                                  str(FIXTURE / 'findings.zizmor-1.30.1.sarif'), '--repo',
                                  str(self.root), '--preview-repairs'], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0)
        self.assertEqual(json.loads(process.stdout)['packets'][0]['repair']['status'], 'proposed')

    def test_quoted_and_flow_run_forms_refuse(self):
        source = SOURCE.replace('        run: |\n          printf \'%s\\n\' "${{ github.event.pull_request.title }}"\n',
                                '        run: "printf literal"\n')
        doc = copy.deepcopy(SARIF)
        region = doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region']
        region.clear()
        region.update({'startLine': 11, 'snippet': {'text': 'printf literal'}})
        packet = self.report(source, doc)['packets'][0]
        self.assertEqual(packet['decision'], 'review')
        self.assertIn('literal run', packet['repair']['reason'])

    def test_repair_rejects_unconventional_path(self):
        packet = self.report(sarif=SARIF)['packets'][0]
        workflow = Workflow.parse('other.yml', SOURCE.encode())
        with self.assertRaisesRegex(RepairError, 'conventional'):
            transform(workflow, packet['evidence'][0])
