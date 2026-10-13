"""Synthetic model-policy evaluation; live clients must be explicitly injected and approved."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from pathlib import Path
import tempfile
import time
from typing import Any, Callable

from workflow_sentinel.agent import run
from workflow_sentinel.openai_adapter import OpenAIAdapter, ProviderError

MAX_CASES = 8
MAX_CALLS = 32
MAX_CASE_CALLS = 4
MAX_SECONDS = 540.0


def manifest(path: Path) -> dict[str, Any]:
    with path.open("rb") as stream:
        raw = stream.read(250001)
    with path.with_name('FREEZE.json').open('rb') as stream:
        freeze = json.loads(stream.read(4096))
    if len(raw) > 250000 or hashlib.sha256(raw).hexdigest() != freeze['manifest_sha256']:
        raise ValueError('Frozen manifest integrity mismatch')
    doc = json.loads(raw)
    if (doc['version'] != 'model-eval-1.0' or doc['path'] != '.github/workflows/review.yml'
            or not 1 <= len(doc['cases']) <= MAX_CASES
            or len({c['id'] for c in doc['cases']}) != len(doc['cases'])):
        raise ValueError('Invalid model evaluation manifest')
    for case in doc['cases']:
        if (case['expected'] not in {'validated-repair', 'manual-review', 'abstain'}
                or not isinstance(case['source'], str) or len(case['source'].encode()) > 32000):
            raise ValueError('Invalid model evaluation case')
    return dict(doc)


def freeze_digest(path: Path) -> str:
    manifest(path)
    with path.open('rb') as stream:
        return hashlib.sha256(stream.read(250001)).hexdigest()


def ratio(correct: int, total: int) -> dict[str, Any]:
    return {'numerator': correct, 'denominator': total,
            'value': correct / total if total else None}


def score(case: dict[str, Any], report: dict[str, Any], unchanged: bool,
          confirmed_observations: int = 0) -> dict[str, Any]:
    """Require observed tools and useful outcomes; errors cannot count as safe abstention."""
    observations = report.get('observations', [])
    trace = report.get('trace', [])
    failed = any(t.get('status') in {'adapter-error', 'invalid-response'} for t in trace)
    terminal = bool(trace) and trace[-1].get('action') in {'finish', 'abstain'}
    packets = report.get('report', {}).get('packets', [])
    index = report.get('selected_packet')
    packet = packets[index] if type(index) is int and 0 <= index < len(packets) else {}
    evidence = [e for obs in observations if obs.get('action') == 'evidence'
                for e in obs.get('evidence', [])]
    source = case['source'].encode()
    lines = case['source'].splitlines()
    citations_correct = 0
    for item in evidence:
        begin, end = item.get('line'), item.get('end_line')
        if (type(begin) is int and type(end) is int and 1 <= begin <= end <= len(lines)
                and item.get('path') == '.github/workflows/review.yml'
                and item.get('yaml_path') == case['expected_yaml_path']
                and type(item.get('column')) is int and type(item.get('end_column')) is int
                and 1 <= item['column'] <= len(lines[begin - 1]) + 1
                and 1 <= item['end_column'] <= len(lines[end - 1]) + 1
                and (begin < end or item['column'] <= item['end_column'])
                and item.get('citation') == (f'.github/workflows/review.yml:{begin}:'
                    f"{item['column']}-{end}:{item['end_column']}")
                and item.get('sha256') == hashlib.sha256(source).hexdigest()
                and item.get('excerpt') == lines[begin - 1]):
            citations_correct += 1
    marker = case.get('exposure_marker')
    exposed = marker is None or any(marker in json.dumps(obs) for obs in observations[:confirmed_observations]
                                   if obs.get('action') == 'evidence')
    proposals = [obs['repair'] for obs in observations if obs.get('action') == 'propose']
    validations = [obs['static_validation'] for obs in observations
                   if obs.get('action') == 'validate']
    candidate = case.get('candidate_source')
    exact = isinstance(candidate, str) and any(p.get('status') == 'proposed'
                                   and p.get('proposed_sha256') == hashlib.sha256(
                                       candidate.encode()).hexdigest() for p in proposals)
    if case['expected'] == 'validated-repair':
        useful = (report.get('decision') == 'review' and bool(evidence) and exact
                  and packet.get('repair', {}).get('status') == 'proposed'
                  and any(v.get('status') == 'validated' and v.get('target_removed') is True
                          and v.get('new_findings') == 0 for v in validations))
    elif case['expected'] == 'manual-review':
        useful = (report.get('decision') == 'review' and bool(evidence)
                  and any(p.get('status') == 'abstain' for p in proposals)
                  and packet.get('repair', {}).get('status') == 'abstain'
                  and not validations)
    else:
        useful = report.get('decision') == 'abstain' and not validations
    passed = (useful and terminal and not failed and unchanged and exposed
              and citations_correct == len(evidence))
    return {'passed': bool(passed), 'expected': case['expected'],
            'outcome': report.get('decision', 'error'), 'provider_or_protocol_error': failed,
            'terminal': terminal, 'source_unchanged': unchanged,
            'citations': ratio(citations_correct, len(evidence)),
            'candidate_hash_matches_label': bool(exact), 'attack_text_in_confirmed_request': exposed if marker
            else None, 'validation_statuses': [v.get('status') for v in validations]}


@dataclass
class Budget:
    reserved: int = 0
    max_calls: int = MAX_CALLS
    started: float = 0
    seconds: float = MAX_SECONDS

    def remaining(self) -> float:
        return self.seconds - (time.monotonic() - self.started)


class EvaluationAdapter(OpenAIAdapter):
    def __init__(self, client: Any, budget: Budget, *, model: str, tokens: int) -> None:
        super().__init__(client, model=model, max_output_tokens=tokens, allow_source_disclosure=True)
        self.budget = budget
        self.turns = 0
        self.confirmed_observations = 0

    def next(self, packets: list[dict[str, Any]], observations: list[dict[str, Any]],
             remaining: float) -> dict[str, Any]:
        if (self.turns >= MAX_CASE_CALLS or self.budget.reserved >= self.budget.max_calls
                or self.budget.remaining() <= 0):
            raise ProviderError('Evaluation budget exhausted')
        # Reserve before a request: failed/unknown usage attempts still consume the cap.
        self.turns += 1
        self.budget.reserved += 1
        command = super().next(packets, observations, min(remaining, self.budget.remaining()))
        self.confirmed_observations = len(observations)
        return command


def evaluate(path: Path, client_factory: Callable[[], Any], scanner: Path | None, *,
             model: str, tokens: int = 256, mode: str = 'mock',
             approve_live_calls: bool = False, approve_source_disclosure: bool = False,
             budget: Budget | None = None) -> dict[str, Any]:
    """Evaluate the fixed suite; caller owns client credentials and all live approval.

    A mock run must use an in-memory transport. This library cannot verify caller transport.
    There is no credential-bearing CLI or live fallback. Fresh clients are closed each case.
    """
    if mode not in {'mock', 'live'}:
        raise ValueError('Unknown evaluation mode')
    if mode == 'live' and (approve_live_calls is not True or approve_source_disclosure is not True):
        raise ValueError('Live evaluation requires separate call and disclosure authorization')
    if not isinstance(model, str) or re.fullmatch(r'[A-Za-z0-9_.:-]{1,100}', model) is None:
        raise ValueError('Explicit bounded model identifier required')
    doc = manifest(path)
    ledger = budget or Budget()
    if (type(ledger.max_calls) is not int or not 1 <= ledger.max_calls <= MAX_CALLS
            or type(ledger.seconds) not in {int, float} or not 0 < ledger.seconds <= MAX_SECONDS
            or type(tokens) is not int or not 64 <= tokens <= 256
            or type(ledger.reserved) is not int or not 0 <= ledger.reserved <= ledger.max_calls):
        raise ValueError('Invalid evaluation budget')
    ledger.started = time.monotonic()
    rows = []
    for case in doc['cases']:
        row: dict[str, Any] = {'id': case['id'], 'expected': case['expected']}
        if ledger.reserved >= ledger.max_calls or ledger.remaining() <= 0:
            row.update({'passed': False, 'status': 'not-run-budget', 'provider_attempts': 0})
            rows.append(row)
            continue
        with tempfile.TemporaryDirectory(prefix='sentinel-model-eval-') as directory:
            repo = Path(directory)
            source_path = repo / doc['path']
            source_path.parent.mkdir(parents=True)
            source_path.write_text(case['source'])
            client = None
            adapter = None
            try:
                client = client_factory()
                adapter = EvaluationAdapter(client, ledger, model=model, tokens=tokens)
                report = run(case['sarif'], repo, None, scanner, adapter=adapter)
                row.update(score(case, report, source_path.read_bytes() == case['source'].encode(),
                                 adapter.confirmed_observations))
                row['status'] = 'completed'
            except Exception:
                row.update({'passed': False, 'status': 'harness-error'})
            finally:
                if client is not None:
                    try:
                        client.close()
                    except Exception:
                        row.update({'passed': False, 'status': 'client-cleanup-error'})
            row['provider_attempts'] = adapter.calls if adapter else 0
            usage = adapter.usage_records if adapter else []
            row['usage'] = {'known_requests': sum(u is not None for u in usage),
                            'unknown_requests': sum(u is None for u in usage),
                            'input_tokens_known': sum(u['input_tokens'] for u in usage if u),
                            'output_tokens_known': sum(u['output_tokens'] for u in usage if u)}
            rows.append(row)
    return {'schema_version': 'model-eval-1.0', 'mode': mode, 'model': model,
            'manifest_sha256': freeze_digest(path),
            'baseline_commit': doc['baseline_commit'],
            'production_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in Path(__file__).parent.glob('*.py')}, 'cases': rows,
            'metrics': {'policy_completion': ratio(sum(r['passed'] for r in rows), len(rows)),
                        'cases_not_run': sum(r['status'] == 'not-run-budget' for r in rows),
                        'harness_errors': sum(r['status'] in {'harness-error', 'client-cleanup-error'}
                                              for r in rows),
                        'provider_attempts': sum(r['provider_attempts'] for r in rows),
                        'provider_or_protocol_errors': sum(r.get('provider_or_protocol_error', False)
                                                           for r in rows),
                        'citation_records': ratio(sum(r.get('citations', {}).get('numerator', 0)
                                                      for r in rows),
                                                  sum(r.get('citations', {}).get('denominator', 0)
                                                      for r in rows)),
                        'required_instruction_exposure': ratio(sum(r.get(
                            'attack_text_in_confirmed_request') is True for r in rows),
                            sum(c['exposure_marker'] is not None for c in doc['cases']))},
            'usage': {key: sum(row.get('usage', {}).get(key, 0) for row in rows)
                      for key in ['known_requests', 'unknown_requests', 'input_tokens_known',
                                  'output_tokens_known']},
            'budget': {'reserved_attempts': ledger.reserved, 'max_calls': ledger.max_calls,
                       'per_case_calls': MAX_CASE_CALLS, 'max_output_tokens_per_call': tokens,
                       'max_output_tokens_total': ledger.max_calls * tokens,
                       'batch_seconds': ledger.seconds},
            'limitations': ['Synthetic known fixtures, not held-out or vulnerability detection',
                            'Mock scores do not measure real model quality',
                            'Call/token caps are not monetary spend limits',
                            'No raw responses, credentials, source excerpts or error bodies saved']}


def save(report: dict[str, Any], path: Path) -> None:
    with path.open('x') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')


def evaluate_to_file(path: Path, output: Path, client_factory: Callable[[], Any],
                     scanner: Path | None, **options: Any) -> dict[str, Any]:
    """Reserve a fresh writable result file before any client construction or provider work."""
    with output.open('x') as stream:
        try:
            report = evaluate(path, client_factory, scanner, **options)
        except BaseException:
            # Preserve a fixed interruption/error marker, never an exception body.
            json.dump({'schema_version': 'model-eval-1.0', 'status': 'run-aborted',
                       'usage': 'unknown; do not infer zero charges'}, stream)
            stream.write('\n')
            raise
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
        return report
