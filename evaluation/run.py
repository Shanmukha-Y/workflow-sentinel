"""Reproducible synthetic policy evaluation; never execute fixture scripts."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch

from workflow_sentinel.cli import investigate
from workflow_sentinel.validation import ScannerUnavailable, validate

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'evaluation/manifest.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def loaded_manifest():
    data = MANIFEST.read_bytes()
    frozen = json.loads((ROOT / 'evaluation/FREEZE.json').read_text())
    if digest(data) != frozen['manifest_sha256']:
        raise ValueError('Evaluation manifest differs from frozen labels')
    return json.loads(data)


def effective_split(case):
    audit = json.loads((ROOT / 'evaluation/AUDIT.json').read_text())
    return ('regression-reused' if case['id'] in audit['excluded_from_first_use_holdout']
            else case['split'])


def source_for(case):
    suffix = case.get('append_source', {})
    return case['source'] + suffix.get('text', '') * suffix.get('repeat', 0)


def citation_ok(citation, path, source):
    match = re.fullmatch(re.escape(path) + r':(\d+):(\d+)-(\d+):(\d+)', citation)
    if not match:
        return False
    line, column, end_line, end_column = map(int, match.groups())
    lines = source.split('\n')
    return (1 <= line <= end_line <= len(lines) and 1 <= column <= len(lines[line - 1]) + 1
            and 1 <= end_column <= len(lines[end_line - 1]) + 1
            and (line != end_line or column <= end_column))


def scanner_documents(case, candidate):
    """Controlled fault-injection data, explicitly separate from real scanner results."""
    before = copy.deepcopy(case['sarif'])
    after = copy.deepcopy(before)
    after['runs'][0]['results'] = []
    scenario = case['scanner_scenario']
    original = copy.deepcopy(before['runs'][0]['results'][0])

    def warning(text, level='error', on_run=False):
        result = copy.deepcopy(original)
        result['ruleId'] = 'zizmor/evaluation-warning'
        result['level'] = level
        line = next(i + 1 for i, s in enumerate(text.splitlines()) if 'printf ' in s) if on_run else 1
        result['locations'][0]['physicalLocation']['region'] = {
            'startLine': line, 'snippet': {'text': text.splitlines()[line - 1].strip()}}
        return result

    if scenario == 'new':
        after['runs'][0]['results'] = [warning(candidate)]
    elif scenario == 'strengthened':
        before['runs'][0]['results'].append(warning(case['source'], 'warning'))
        after['runs'][0]['results'] = [warning(candidate, 'error')]
    elif scenario == 'shifted':
        before['runs'][0]['results'].append(warning(case['source'], on_run=True))
        after['runs'][0]['results'] = [warning(candidate, on_run=True)]
    elif scenario == 'retained':
        result = warning(candidate, on_run=True)
        result['ruleId'] = 'zizmor/template-injection'
        after['runs'][0]['results'] = [result]
    elif scenario == 'missing':
        before['runs'][0]['results'] = []
    elif scenario == 'malformed':
        return [{}]
    else:
        raise ValueError('Unknown frozen scanner fault scenario')
    return [before, after]


def check_diff(repair, path, source, expected_source):
    # Fixed git argv; the generated diff is data. Reject other file headers before applying it.
    diff = repair['unified_diff']
    headers = [line for line in diff.splitlines() if line.startswith(('--- ', '+++ '))]
    if headers != ['--- a/' + path, '+++ b/' + path]:
        return False
    with tempfile.TemporaryDirectory(prefix='sentinel-eval-diff-') as temp:
        destination = Path(temp) / path
        destination.parent.mkdir(parents=True)
        destination.write_text(source)
        process = subprocess.run(['git', 'apply', '-'], input=diff, text=True, cwd=temp,
                                 capture_output=True, timeout=5)
        return (process.returncode == 0 and destination.read_text() == expected_source
                and digest(destination.read_bytes()) == repair['proposed_sha256'])


def evaluate_case(case, path, scanner):
    expected = case['expected']
    source = source_for(case)
    row = {'id': case['id'], 'category': case['category'], 'split': effective_split(case),
           'expected': {k: v for k, v in expected.items() if k != 'candidate_source'},
           'triage': None, 'repair': 'not-run', 'validation': 'not-run',
           'validation_mode': 'not-run', 'source_unchanged': False,
           'citations_correct': 0, 'citations_total': 0, 'repair_exact': None,
           'failures': [], 'source_sha256': digest(source.encode())}
    with tempfile.TemporaryDirectory(prefix='sentinel-eval-') as temp:
        root = Path(temp)
        target = root / path
        target.parent.mkdir(parents=True)
        target.write_text(source)
        try:
            report = investigate(copy.deepcopy(case['sarif']), root, preview_repairs=True)
        except (ValueError, KeyError, TypeError, AttributeError):
            report = None
            row['triage'] = 'error'
        if report is not None:
            packets = report['packets']
            row['triage'] = 'empty' if not packets else packets[0]['decision']
            if packets:
                packet = packets[0]
                row['repair'] = packet['repair']['status']
                for evidence in packet['evidence']:
                    semantic_ok = (evidence['path'] == path and evidence['sha256'] == digest(source.encode())
                                   and evidence['yaml_path'] == expected['yaml_path']
                                   and evidence['excerpt'] == source.splitlines()[evidence['line'] - 1][:500])
                    citations = [evidence['citation'], *evidence['context']['citations'],
                                 *(c['citation'] for c in evidence['context']['checkouts'])]
                    row['citations_total'] += len(citations)
                    row['citations_correct'] += sum(semantic_ok and citation_ok(c, path, source)
                                                    for c in citations)
                if packet['repair']['status'] == 'proposed':
                    row['repair_exact'] = ('candidate_source' in expected and check_diff(
                        packet['repair'], path, source, expected.get('candidate_source', '')))
                    if 'validation' in expected:
                        if 'scanner_scenario' in case:
                            outputs = scanner_documents(case, expected['candidate_source'])
                            with patch('workflow_sentinel.validation.scanner_path',
                                       return_value=Path('/installed/zizmor')):
                                with patch('workflow_sentinel.validation.scan', side_effect=outputs):
                                    checked = validate(packet, root, None)
                            row['validation_mode'] = 'simulated-scanner-fault'
                        elif scanner is not None:
                            checked = validate(packet, root, scanner)
                            row['validation_mode'] = 'live-scanner'
                        else:
                            with patch('workflow_sentinel.validation.scanner_path',
                                       side_effect=ScannerUnavailable('Evaluation live scanner disabled')):
                                preflight = validate(packet, root, None)
                            checked = (None if preflight['reason'] == 'Evaluation live scanner disabled'
                                       else preflight)
                            if checked is not None:
                                row['validation_mode'] = 'preflight-only'
                        if checked is not None:
                            row['validation'] = checked['status']
                            row['validation_detail'] = checked
                            if row['validation_mode'] == 'live-scanner' and checked['attempts'] == 0:
                                row['validation_mode'] = 'preflight-only'
        row['source_unchanged'] = target.read_bytes() == source.encode()
    for field in ['triage', 'repair']:
        if row[field] != expected[field]:
            row['failures'].append(field + ': expected ' + expected[field] + ', observed ' + str(row[field]))
    if 'validation' in expected and row['validation'] != 'not-run':
        if row['validation'] != expected['validation']:
            row['failures'].append('validation: expected ' + expected['validation']
                                   + ', observed ' + row['validation'])
    if row['citations_correct'] != row['citations_total']:
        row['failures'].append('Source citation or labeled YAML-path mismatch')
    if row['repair_exact'] is False:
        row['failures'].append('Diff does not produce the independently labeled candidate')
    if not row['source_unchanged']:
        row['failures'].append('Original source changed')
    row['passed_observed_checks'] = not row['failures']
    return row


def ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'value': numerator / denominator if denominator else None}


def metrics(rows):
    reviews = [r for r in rows if r['triage'] == 'review']
    expected_reviews = [r for r in rows if r['expected']['triage'] == 'review']
    proposals = [r for r in rows if r['repair'] == 'proposed']
    eligible = [r for r in rows if r['expected']['repair'] == 'proposed']
    decisions = [r for r in rows if r['repair'] in {'proposed', 'abstain'}]
    live = [r for r in rows if r['validation_mode'] == 'live-scanner']
    simulated = [r for r in rows if r['validation_mode'] == 'simulated-scanner-fault']
    preflight = [r for r in rows if r['validation_mode'] == 'preflight-only']
    return {
        'observed_case_accuracy': ratio(sum(r['passed_observed_checks'] for r in rows), len(rows)),
        'triage_policy_precision': ratio(sum(r['expected']['triage'] == 'review' for r in reviews), len(reviews)),
        'triage_policy_recall': ratio(sum(r['triage'] == 'review' for r in expected_reviews), len(expected_reviews)),
        'repair_eligibility_precision': ratio(sum(r['expected']['repair'] == 'proposed' for r in proposals), len(proposals)),
        'repair_eligibility_recall': ratio(sum(r['repair'] == 'proposed' for r in eligible), len(eligible)),
        'repair_abstention_rate': ratio(sum(r['repair'] == 'abstain' for r in decisions), len(decisions)),
        'citation_source_checks': ratio(sum(r['citations_correct'] for r in rows), sum(r['citations_total'] for r in rows)),
        'exact_candidate_validity': ratio(sum(r['repair_exact'] is True for r in proposals), len(proposals)),
        'source_immutability': ratio(sum(r['source_unchanged'] for r in rows), len(rows)),
        'live_validation_label_agreement': ratio(sum(r['validation'] == r['expected']['validation'] for r in live), len(live)),
        'preflight_label_agreement': ratio(sum(r['validation'] == r['expected']['validation'] for r in preflight), len(preflight)),
        'real_scanner_calls': sum(r['validation_detail']['attempts'] for r in live),
        'simulated_validation_label_agreement': ratio(sum(r['validation'] == r['expected']['validation'] for r in simulated), len(simulated)),
        'validation_not_run': sum('validation' in r['expected'] and r['validation'] == 'not-run' for r in rows),
        'validation_outcomes': {status: sum(r['validation'] == status for r in rows)
                                for status in ['validated', 'rejected', 'unsupported', 'unavailable', 'not-run']},
    }


def run(split='all', scanner=None, run_kind='regression'):
    manifest = loaded_manifest()
    rows = [evaluate_case(case, manifest['path'], scanner) for case in manifest['cases']
            if split == 'all' or effective_split(case) == split]
    return {'dataset_version': manifest['dataset_version'], 'manifest_sha256': digest(MANIFEST.read_bytes()),
            'production_baseline_commit': manifest['frozen_against_commit'],
            'production_files_sha256': {p.name: digest(p.read_bytes())
                                         for p in sorted((ROOT / 'src/workflow_sentinel').glob('*.py'))},
            'run_kind': run_kind, 'split': split, 'scanner_requested': scanner is not None,
            'methodology': manifest['methodology'], 'metrics': metrics(rows), 'cases': rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=['all', 'development', 'holdout-first-use', 'regression-reused'], default='all')
    parser.add_argument('--scanner', type=Path)
    parser.add_argument('--run-kind', choices=['first-use', 'regression'], default='regression')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; original results must not be overwritten')
    result = run(args.split, args.scanner, args.run_kind)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result['metrics'], indent=2))
    return 1 if any(r['failures'] for r in result['cases']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
