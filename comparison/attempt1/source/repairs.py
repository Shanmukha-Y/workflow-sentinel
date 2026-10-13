"""Constrained source-to-source repair previews; no writes or command execution."""
from __future__ import annotations

import copy
import difflib
import hashlib
import re
from typing import Any

from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from workflow_sentinel.investigation import Workflow, mapping, scalar

ALLOWED_EXPRESSIONS = {
    'github.event.pull_request.title', 'github.event.pull_request.body',
    'github.event.issue.title', 'github.event.issue.body', 'github.head_ref',
}
VARIABLE = 'SENTINEL_INPUT'
PRINTF = re.compile(r'''printf ('%s(?:\\n)?') "\$\{\{ ([a-z._]+) \}\}"\n?''')


class RepairError(ValueError):
    pass


def tree(node: Node) -> Any:
    if isinstance(node, MappingNode):
        return {key: tree(value) for key, value in mapping(node).items()}
    if isinstance(node, SequenceNode):
        return [tree(value) for value in node.value]
    if isinstance(node, ScalarNode):
        return scalar(node)
    raise RepairError('Unsupported YAML structure')


def transform(workflow: Workflow, evidence: dict[str, Any]) -> str:
    if re.fullmatch(r'\.github/workflows/[A-Za-z0-9_.-]+\.ya?ml', workflow.path) is None:
        raise RepairError('Repair requires a conventional .github/workflows YAML path')
    if evidence['provenance'] not in {'snippet-matched', 'hash-matched'}:
        raise RepairError('Repair requires a matching SARIF source snippet or hash')
    if evidence['sha256'] != hashlib.sha256(workflow.raw).hexdigest():
        raise RepairError('Evidence does not match the source snapshot')
    route = evidence['yaml_path']
    if (len(route) != 5 or route[0] != 'jobs' or route[2] != 'steps'
            or type(route[3]) is not int or route[4] != 'run'):
        raise RepairError('Finding must identify a single step run scalar')
    job_id, step_index = route[1], route[3]
    data = mapping(workflow.root)
    job = mapping(mapping(data['jobs'])[job_id])
    steps = job.get('steps')
    if not isinstance(steps, SequenceNode):
        raise RepairError('Unsupported steps structure')
    step_node = steps.value[step_index]
    step = mapping(step_node)
    if 'shell' not in step or scalar(step['shell']) != 'bash':
        raise RepairError('Repair requires an explicit step shell: bash')
    if any('env' in group for group in [data, job, step]):
        raise RepairError('Existing environment declarations require manual review')
    if 'container' in job or 'defaults' in data or 'defaults' in job:
        raise RepairError('Container or default execution settings require manual review')
    run = step.get('run')
    if not isinstance(run, ScalarNode) or run.style != '|':
        raise RepairError('Only a literal run: | block is supported')
    match = PRINTF.fullmatch(scalar(run))
    if match is None or match[2] not in ALLOWED_EXPRESSIONS:
        raise RepairError('Only one printf command with a supported untrusted expression is supported')
    if VARIABLE in workflow.text:
        raise RepairError('Generated environment variable would collide with existing source')
    key = next(key for key, _ in step_node.value if scalar(key) == 'run')
    line_start = workflow.text.rfind('\n', 0, key.start_mark.index) + 1
    line_end = workflow.text.find('\n', key.start_mark.index)
    if line_end < 0:
        raise RepairError('Run block must have a terminated header line')
    header = workflow.text[line_start:line_end]
    if re.fullmatch(r' +run: \|', header) is None:
        raise RepairError('Unsupported run header, indentation or comments')
    if '\r' in workflow.text or not workflow.text.endswith('\n'):
        raise RepairError('Repair requires LF source with a final newline')
    indent = ' ' * key.start_mark.column
    expression = '${{ ' + match[2] + ' }}'
    new_run = f'printf {match[1]} "${VARIABLE}"\n'
    replacement = '|\n' + indent + '  ' + new_run
    edited = (workflow.text[:run.start_mark.index] + replacement
              + workflow.text[run.end_mark.index:])
    edited = (edited[:line_start] + indent + 'env:\n' + indent + '  ' + VARIABLE
              + ': ' + expression + '\n' + edited[line_start:])
    parsed = Workflow.parse(workflow.path, edited.encode())
    expected = copy.deepcopy(tree(workflow.root))
    expected_step = expected['jobs'][job_id]['steps'][step_index]
    expected_step['run'] = new_run
    expected_step['env'] = {VARIABLE: expression}
    if tree(parsed.root) != expected:
        raise RepairError('Proposed edit changes YAML outside the allowlisted run/env fields')
    return str(edited)


def preview(packet: dict[str, Any], workflows: dict[str, Workflow]) -> dict[str, Any]:
    refused: dict[str, Any] = {'status': 'abstain', 'reason': '', 'unified_diff': None,
                               'path': None, 'base_sha256': None, 'proposed_sha256': None,
                               'validation': []}
    if packet['rule_id'] == 'dangerous-triggers':
        refused['reason'] = 'Untrusted checkout and trigger changes remain report-only'
        return refused
    if packet['rule_id'] == 'excessive-permissions':
        refused['reason'] = 'Permission repairs require explicit validated requirements; not supported'
        return refused
    if packet['rule_id'] != 'template-injection' or packet['decision'] != 'review':
        refused['reason'] = 'No supported, source-resolved injection finding'
        return refused
    if len(packet['evidence']) != 1:
        refused['reason'] = 'Repair requires exactly one source location'
        return refused
    evidence = packet['evidence'][0]
    try:
        workflow = workflows[evidence['path']]
        edited = transform(workflow, evidence)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        refused['reason'] = str(exc) if isinstance(exc, RepairError) else 'Unsupported source context'
        return refused
    diff = ''.join(difflib.unified_diff(workflow.text.splitlines(keepends=True),
                                       edited.splitlines(keepends=True),
                                       fromfile='a/' + workflow.path,
                                       tofile='b/' + workflow.path))
    if len(diff) > 16_000:
        refused['reason'] = 'Proposed diff exceeds preview size limit'
        return refused
    return {'status': 'proposed', 'reason': 'Move expression from script generation to quoted Bash env',
            'path': workflow.path, 'base_sha256': evidence['sha256'],
            'proposed_sha256': hashlib.sha256(edited.encode()).hexdigest(), 'unified_diff': diff,
            'validation': ['YAML reparsed', 'Only selected run and new step env changed',
                           'Base hash binds the reviewed source; verify it before applying',
                           'Human review required; static checks do not prove security']}
