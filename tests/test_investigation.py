import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import validate

from workflow_sentinel.cli import investigate
from workflow_sentinel.investigation import RepositoryReader

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = '''on: [pull_request_target, workflow_dispatch]
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
'''


def document(line=15, column=None, snippet=None):
    region = {'startLine': line}
    if column is not None:
        region['startColumn'] = column
    if snippet is not None:
        region['snippet'] = {'text': snippet}
    return {'version': '2.1.0', 'runs': [{'tool': {'driver': {'name': 'zizmor'}},
            'results': [{'ruleId': 'zizmor/template-injection', 'locations': [{
                'physicalLocation': {'artifactLocation': {'uri': 'workflow.yml'},
                                     'region': region}}]}]}]}


class InvestigationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'workflow.yml').write_text(WORKFLOW)

    def report(self, doc=None, text=None):
        if text is not None:
            (self.root / 'workflow.yml').write_text(text)
        report = investigate(doc or document(), self.root)
        validate(report, json.loads((ROOT / 'schemas/report.schema.json').read_text()))
        return report['packets'][0]

    def test_multiline_context_permissions_env_and_precise_citations(self):
        packet = self.report(document(column=11))
        self.assertEqual(packet['decision'], 'review')
        evidence = packet['evidence'][0]
        self.assertEqual(evidence['yaml_path'], ['jobs', 'check', 'steps', 1, 'run'])
        self.assertEqual(evidence['citation'], 'workflow.yml:15:11-15:56')
        context = evidence['context']
        self.assertEqual(context['triggers'], ['pull_request_target', 'workflow_dispatch'])
        self.assertEqual(context['permissions'], {'source': 'job', 'declaration': {}})
        self.assertEqual(context['job'], 'check')
        self.assertEqual(context['step_index'], 1)
        self.assertEqual(context['shell'], 'bash')
        self.assertEqual(context['run_expressions'], ['github.event.pull_request.title'])
        self.assertEqual(context['env_expressions'], {'TITLE': ['github.event.pull_request.title']})
        self.assertEqual(context['checkouts'][0]['ref'],
                         '${{ github.event.pull_request.head.sha }}')
        self.assertTrue(any(c.startswith('workflow.yml:5:') for c in context['citations']))
        self.assertEqual(evidence['provenance'], 'unverified')
        self.assertTrue(any(t.startswith('context:') for t in packet['trace']))

    def test_next_line_after_block_scalar_is_not_ambiguous(self):
        packet = self.report(document(line=17))
        self.assertEqual(packet['decision'], 'review')
        context = packet['evidence'][0]['context']
        self.assertEqual(context['shell'], 'bash')
        self.assertEqual(context['step_if'], "github.event_name == 'pull_request_target'")

    def test_workflow_scope_includes_checkout_across_jobs(self):
        packet = self.report(document(line=1, column=1))
        context = packet['evidence'][0]['context']
        self.assertEqual(context['job'], None)
        self.assertEqual(context['permissions']['source'], 'workflow')
        self.assertEqual(context['checkouts'][0]['job'], 'check')

    def test_repository_defaults_are_unknown(self):
        packet = self.report(text=WORKFLOW.replace('permissions: write-all\n', '')
                             .replace('    permissions: {}\n', ''),
                             doc=document(line=13))
        self.assertEqual(packet['decision'], 'review')
        self.assertEqual(packet['evidence'][0]['context']['permissions'],
                         {'source': 'repository-default', 'declaration': None})

    def test_matching_and_stale_snippets(self):
        run_text = 'echo "${{ github.event.pull_request.title }}"\nprintf \'%s\' "$TITLE"\n'
        packet = self.report(document(snippet=run_text))
        self.assertEqual(packet['evidence'][0]['provenance'], 'snippet-matched')
        packet = self.report(document(snippet='old source'))
        self.assertEqual(packet['decision'], 'abstain')
        self.assertIn('source snippet mismatch', packet['reason'])
        self.assertEqual(packet['evidence'], [])

    def test_artifact_index_hash_provenance_and_disagreement(self):
        doc = document()
        artifact = doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['artifactLocation']
        artifact.clear()
        artifact['index'] = 0
        doc['runs'][0]['artifacts'] = [{'location': {'uri': 'workflow.yml'},
                                      'hashes': {'sha-256': hashlib.sha256(
                                          WORKFLOW.encode()).hexdigest()}}]
        self.assertEqual(self.report(doc)['evidence'][0]['provenance'], 'hash-matched')
        doc['runs'][0]['artifacts'][0]['hashes']['sha-256'] = '0' * 64
        self.assertIn('source hash mismatch', self.report(doc)['reason'])
        artifact['uri'] = 'other.yml'
        self.assertIn('path disagrees with index', self.report(doc)['reason'])

    def test_ambiguous_line_comments_and_invalid_regions_abstain(self):
        self.assertIn('no unique YAML node', self.report(
            document(line=1), '# comment\n' + WORKFLOW)['reason'])
        self.assertIn('no unique YAML node', self.report(
            document(line=2), 'on: push\njobs: {a: {}, b: {}}\n')['reason'])
        for region in [{'startLine': 999}, {'startLine': True},
                       {'startLine': 15, 'startColumn': 999},
                       {'startLine': 15, 'endLine': 1},
                       {'startLine': 15, 'endColumn': 999}]:
            doc = document()
            doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region'] = region
            self.assertEqual(self.report(doc)['decision'], 'abstain')

    def test_duplicate_alias_tag_merge_multiple_documents_abstain(self):
        texts = [WORKFLOW + 'jobs: {}\n', WORKFLOW.replace('permissions: write-all',
                 'permissions: &p write-all'),
                 'on: push\njobs: !!python/object/apply:os.system ["touch /tmp/forbidden"]\n',
                 'on: push\njobs: {<<: {a: {}}}\n', WORKFLOW + '\n---\njobs: {}\n',
                 'on: push\njobs: [\n']
        for text in texts:
            with self.subTest(text=text[:30]):
                self.assertEqual(self.report(document(line=1), text)['decision'], 'abstain')

    def test_yaml_depth_and_node_budgets(self):
        text = 'on: push\njobs: ' + '[' * 33 + 'x' + ']' * 33
        self.assertIn('depth budget', self.report(document(line=1), text)['reason'])
        text = 'on: push\njobs: {}\nextra: [' + ','.join(['x'] * 5000) + ']'
        self.assertIn('node budget', self.report(document(line=1), text)['reason'])

    def test_context_and_read_budgets(self):
        text = 'on: push\njobs:\n' + ''.join(f'  j{i}: {{}}\n' for i in range(31))
        self.assertIn('job context budget', self.report(document(line=1), text)['reason'])
        with patch('workflow_sentinel.investigation.MAX_TOTAL_BYTES', 10):
            self.assertIn('byte budget', self.report(document(line=1))['reason'])
        reader = RepositoryReader(self.root)
        with patch('workflow_sentinel.investigation.MAX_FILES', 0):
            with self.assertRaisesRegex(ValueError, 'file budget'):
                reader.read(Path('workflow.yml'))

    def test_repeated_locations_share_one_snapshot(self):
        doc = document()
        result = doc['runs'][0]['results'][0]
        doc['runs'][0]['results'].append(copy.deepcopy(result))
        original = RepositoryReader.read
        calls = []

        def counted(reader, path):
            calls.append(path)
            return original(reader, path)

        with patch.object(RepositoryReader, 'read', counted):
            report = investigate(doc, self.root)
        self.assertEqual(len(calls), 1)
        self.assertEqual(report['packets'][0], report['packets'][1])

    def test_intermediate_symlink_and_non_regular_file(self):
        (self.root / 'link').symlink_to(self.root, target_is_directory=True)
        doc = document()
        doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['artifactLocation'][
            'uri'] = 'link/workflow.yml'
        self.assertEqual(self.report(doc)['decision'], 'abstain')
        (self.root / 'directory.yml').mkdir()
        reader = RepositoryReader(self.root)
        with self.assertRaisesRegex(ValueError, 'not a regular file'):
            reader.read(Path('directory.yml'))

    def test_unicode_column_conversion_and_missing_kind(self):
        text = 'on: push\njobs: {check: {steps: [{name: "😀", run: echo}]}}\n'
        codepoint = text.splitlines()[1].index('echo') + 1
        doc = document(line=2, column=codepoint + 1)
        doc['runs'][0]['columnKind'] = 'utf16CodeUnits'
        packet = self.report(doc, text)
        self.assertEqual(packet['decision'], 'review')
        self.assertEqual(packet['evidence'][0]['column'], codepoint)
        self.assertEqual(packet['evidence'][0]['column_kind'], 'unicodeCodePoints')
        doc['runs'][0]['columnKind'] = 'unicodeCodePoints'
        doc['runs'][0]['results'][0]['locations'][0]['physicalLocation']['region'][
            'startColumn'] = codepoint
        self.assertEqual(self.report(doc)['decision'], 'review')
        del doc['runs'][0]['columnKind']
        self.assertIn('column kind required', self.report(doc)['reason'])

    def test_provenance_conflicts_and_invalid_column_kind_abstain(self):
        doc = document()
        meta = {'location': {'uri': 'workflow.yml'}, 'hashes': {'sha-256': '0' * 64}}
        doc['runs'][0]['artifacts'] = [meta, copy.deepcopy(meta)]
        self.assertIn('ambiguous SARIF artifact', self.report(doc)['reason'])
        doc = document(column=11)
        doc['runs'][0]['columnKind'] = 'byteOffset'
        self.assertIn('unsupported SARIF column kind', self.report(doc)['reason'])

    def test_hash_metadata_uses_normalized_relative_path(self):
        doc = document()
        doc['runs'][0]['artifacts'] = [{'location': {'uri': './workflow.yml'},
                                      'hashes': {'sha-256': '0' * 64}}]
        self.assertIn('source hash mismatch', self.report(doc)['reason'])

    def test_failed_reads_consume_file_budget(self):
        reader = RepositoryReader(self.root)
        with patch('workflow_sentinel.investigation.MAX_FILES', 1):
            with self.assertRaises(OSError):
                reader.read(Path('missing.yml'))
            with self.assertRaisesRegex(ValueError, 'file budget'):
                reader.read(Path('workflow.yml'))
