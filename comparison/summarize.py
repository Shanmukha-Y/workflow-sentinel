"""Derive descriptive statistics exclusively from retained real comparison records."""
import argparse
import json
from pathlib import Path
import statistics


def ratio(rows):
    return {'successes': sum(c['passed'] for c in rows), 'cases': len(rows)}


def summarize(directory):
    index = json.loads((directory / 'index.json').read_text())
    result = {'protocol_version': index['protocol']['version'], 'models': [],
              'total_wall_seconds': index['wall_seconds'],
              'reserved_requests': index['reserved_requests']}
    for model in index['protocol']['models']:
        reports = [json.loads((directory / r['file']).read_text()) for r in index['rows']
                   if r['model'] == model]
        assert all(r['mode'] == 'local' and r['capture_raw_evidence'] for r in reports)
        digests = {c['model_metadata']['digest'] for r in reports for c in r['cases']
                   if 'model_metadata' in c}
        assert len(digests) == 1, 'Model weights changed within comparison'
        cases = [c for r in reports for c in r['cases']]
        attempts = [a for c in cases for a in c.get('attempts', [])]
        memory = [a['sampled_model_memory_bytes'] for a in attempts
                  if 'sampled_model_memory_bytes' in a]
        fresh = [r for r in reports if r['comparison']['group'] == 'fresh']
        categories = sorted({c['category'] for r in fresh for c in r['cases']})
        cold = {str(r['comparison']['trial']): r['comparison']['cold_preload']['wall_seconds']
                for r in reports}
        latency = [a['wall_seconds'] for a in attempts]
        completed_latency = [a['wall_seconds'] for c in cases if c['passed']
                             for a in c.get('attempts', [])]
        result['models'].append({'model': model, 'digest': next(iter(digests)),
            'download_bytes': index['models'][model]['download_bytes'],
            'details': index['models'][model]['details'],
            'all_cases': ratio(cases),
            'fresh_trials': [{'trial': r['comparison']['trial'], **ratio(r['cases']),
                              'wall_seconds': r['wall_seconds']} for r in fresh],
            'fresh_by_category': {k: {**ratio([c for r in fresh for c in r['cases']
                                           if c['category'] == k]),
                'median_successful_case_seconds': statistics.median([c['wall_seconds']
                    for r in fresh for c in r['cases'] if c['category'] == k and c['passed']])
                    if any(c['category'] == k and c['passed']
                           for r in fresh for c in r['cases']) else None} for k in categories},
            'invalid_tool_attempts': sum(c.get('invalid_tool_attempts', 0) for c in cases),
            'disallowed_tool_attempts': sum(c.get('disallowed_tool_attempts', 0) for c in cases),
            'observed_gate_breaches': sum(c.get('observed_gate_breaches', 0) for c in cases),
            'gate_checked_cases': sum('observed_gate_breaches' in c for c in cases),
            'attempts': len(attempts),
            'median_attempt_seconds': statistics.median(latency) if latency else None,
            'median_successful_attempt_seconds': statistics.median(completed_latency)
                if completed_latency else None,
            'sampled_max_model_memory_bytes': max(memory) if memory else None,
            'memory_samples': len(memory), 'cold_preload_seconds': cold,
            'known_prompt_tokens': sum(r['usage']['input_tokens_known'] for r in reports),
            'known_output_tokens': sum(r['usage']['output_tokens_known'] for r in reports),
            'unknown_usage_requests': sum(r['usage']['unknown_requests'] for r in reports)})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    summary = summarize(args.directory)
    with args.output.open('x') as stream:
        json.dump(summary, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
