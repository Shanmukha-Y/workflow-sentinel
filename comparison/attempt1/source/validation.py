"""Opt-in bounded static validation of a single-workflow repair candidate."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Any

from workflow_sentinel.investigation import Investigator, RepositoryReader, Workflow, relative_path
from workflow_sentinel.repairs import preview, transform, tree

SCANNER_ARGS = ('--offline', '--format=sarif', '--strict-collection', '--no-config',
                '--no-ignores', '--persona=regular', '--color=never', '.')
TIMEOUT_SECONDS = 15
MAX_STDOUT = 1_000_000
MAX_STDERR = 64_000
MAX_VALIDATIONS = 2
SUPPORTED_VERSION = '1.30.1'


class ScannerUnavailable(ValueError):
    pass


class ComparisonUnsupported(ValueError):
    pass


def scanner_path(repo: Path, configured: Path | None) -> Path:
    candidate = configured or (Path(found) if (found := shutil.which('zizmor')) else None)
    if candidate is None or not candidate.is_absolute():
        raise ScannerUnavailable('Installed zizmor binary unavailable; specify its absolute path')
    executable = candidate.resolve()
    if executable.is_relative_to(repo.resolve()):
        raise ScannerUnavailable('Scanner executable must be installed outside the target repository')
    if (executable.name != 'zizmor' or not executable.is_file()
            or not os.access(executable, os.X_OK)):
        raise ScannerUnavailable('Scanner must be an executable installed zizmor binary')
    try:
        with executable.open('rb') as stream:
            magic = stream.read(4)
    except OSError as exc:
        raise ScannerUnavailable('Scanner executable cannot be read') from exc
    if magic not in {b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf',
                     b'\xce\xfa\xed\xfe', b'\xfe\xed\xfa\xce', b'\xca\xfe\xba\xbe'}:
        raise ScannerUnavailable('Scanner wrappers and scripts are unsupported; use a native binary')
    return executable


def scan(executable: Path, directory: Path) -> dict[str, Any]:
    # Explicit arguments and a scrubbed environment; repository text cannot supply commands.
    environment = {'PATH': '/usr/bin:/bin', 'HOME': str(directory), 'TMPDIR': str(directory),
                   'XDG_CACHE_HOME': str(directory), 'ZIZMOR_OFFLINE': '1', 'NO_COLOR': '1'}
    try:
        process = subprocess.Popen([str(executable), *SCANNER_ARGS], cwd=directory,
                                   env=environment, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   start_new_session=True)
    except OSError as exc:
        raise ScannerUnavailable('Scanner failed to start') from exc
    deadline = time.monotonic() + TIMEOUT_SECONDS
    output: dict[str, bytearray] = {'stdout': bytearray(), 'stderr': bytearray()}
    try:
        with selectors.DefaultSelector() as selector:
            for name, stream in [('stdout', process.stdout), ('stderr', process.stderr)]:
                assert stream is not None
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ScannerUnavailable('Scanner timed out')
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fd, 16_384)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    name = key.data
                    limit = MAX_STDOUT if name == 'stdout' else MAX_STDERR
                    if len(output[name]) + len(chunk) > limit:
                        raise ScannerUnavailable('Scanner output exceeded byte limit')
                    output[name].extend(chunk)
            try:
                code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired as exc:
                raise ScannerUnavailable('Scanner timed out') from exc
        if code != 0:
            raise ScannerUnavailable('Scanner exited with a failure status')
        try:
            document = json.loads(output['stdout'])
        except (ValueError, UnicodeError, RecursionError) as exc:
            raise ScannerUnavailable('Scanner output is not valid JSON') from exc
        if not isinstance(document, dict):
            raise ScannerUnavailable('Scanner output is not a SARIF object')
        return document
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                stream.close()


def findings(document: dict[str, Any], directory: Path,
             expected_path: str) -> tuple[Counter[str], Counter[str], str]:
    """Compare rule/level/severity and structural routes, preserving duplicate multiplicity."""
    if document.get('version') != '2.1.0' or not isinstance(document.get('runs'), list):
        raise ScannerUnavailable('Scanner output is not SARIF 2.1.0')
    if len(document['runs']) != 1:
        raise ComparisonUnsupported('Only one scanner run can be compared')
    run = document['runs'][0]
    try:
        driver = run['tool']['driver']
        version = driver.get('semanticVersion', driver.get('version'))
        if driver['name'] != 'zizmor' or not isinstance(version, str):
            raise ValueError
        if version != SUPPORTED_VERSION:
            raise ComparisonUnsupported('Scanner version is unsupported for validation')
        invocations = run['invocations']
        if not invocations or any(i.get('executionSuccessful') is not True for i in invocations):
            raise ValueError
        results = run['results']
        if not isinstance(results, list) or len(results) > 1000:
            raise ValueError
        signatures: Counter[str] = Counter()
        targets: Counter[str] = Counter()
        investigator = Investigator(directory)
        for result in results:
            if result.get('kind', 'fail') != 'fail':
                raise ComparisonUnsupported('Non-failure SARIF result kinds cannot be compared')
            rule = result['ruleId']
            level = result.get('level', 'warning')
            if not isinstance(rule, str) or level not in {'none', 'note', 'warning', 'error'}:
                raise ValueError
            # Only this exact supported alias is normalized for the repair target.
            if rule == 'zizmor/template-injection':
                rule = 'template-injection'
            locations = result['locations']
            if not isinstance(locations, list) or not 1 <= len(locations) <= 10:
                raise ValueError
            routes = []
            for location in locations:
                evidence = investigator.inspect(location, run, [])
                if evidence['path'] != expected_path:
                    raise ComparisonUnsupported('Scanner findings refer outside the isolated workflow')
                routes.append(evidence['yaml_path'])
            properties = result.get('properties', {})
            severity = properties.get('zizmor/severity')
            confidence = properties.get('zizmor/confidence')
            if severity is not None and not isinstance(severity, str):
                raise ValueError
            if confidence is not None and not isinstance(confidence, str):
                raise ValueError
            route_key = json.dumps(sorted(routes, key=lambda r: json.dumps(r)), sort_keys=True)
            signatures[json.dumps([rule, level, severity, confidence, route_key])] += 1
            if rule == 'template-injection':
                for route in routes:
                    targets[json.dumps(route)] += 1
        return signatures, targets, version
    except ComparisonUnsupported:
        raise
    except (KeyError, ValueError, TypeError, AttributeError, OSError, RecursionError) as exc:
        raise ScannerUnavailable('Scanner SARIF has malformed or unresolvable finding evidence') from exc


def validate(packet: dict[str, Any], root: Path,
             executable: Path | None) -> dict[str, Any]:
    result: dict[str, Any] = {'status': 'unsupported', 'reason': 'No eligible repair proposal',
                              'scope': 'single-workflow', 'scanner_version': None,
                              'attempts': 0, 'before_findings': None, 'after_findings': None,
                              'new_findings': None, 'target_removed': None, 'checks': []}
    repair = packet.get('repair', {})
    if repair.get('status') != 'proposed':
        return result
    try:
        path = relative_path({'uri': repair['path']})
        raw = RepositoryReader(root).read(path)
        if hashlib.sha256(raw).hexdigest() != repair['base_sha256']:
            raise ValueError('Current source differs from the proposal base hash')
        workflow = Workflow.parse(path.as_posix(), raw)
        # Reconstruct the allowlisted edit instead of interpreting an arbitrary supplied diff.
        reconstructed = preview(packet, {workflow.path: workflow})
        if reconstructed != repair or reconstructed['status'] != 'proposed':
            raise ValueError('Proposal differs from the reconstructed allowlisted repair')
        edited = transform(workflow, packet['evidence'][0])
        if hashlib.sha256(edited.encode()).hexdigest() != repair['proposed_sha256']:
            raise ValueError('Candidate hash differs from proposal')
        Workflow.parse(workflow.path, edited.encode())
        result['checks'] = ['Current base hash matched', 'Exact allowlisted diff reconstructed',
                            'Candidate YAML and scope checked']
        # Missing local actions must not cause misleading incomplete comparisons or reads outside
        # the disposable snapshot. Only syntactically remote action references are supported.
        def check_uses(value: Any) -> None:
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == 'uses' and (not isinstance(child, str) or re.fullmatch(
                        r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*'
                        r'@[A-Za-z0-9_.\-/]+', child
                    ) is None or any(part in {'.', '..'}
                                     for part in child.split('@')[0].split('/'))):
                        raise ComparisonUnsupported('Local, dynamic or nonstandard action refs unsupported')
                    check_uses(child)
            elif isinstance(value, list):
                for child in value:
                    check_uses(child)
        check_uses(tree(workflow.root))
    except ComparisonUnsupported as exc:
        result['reason'] = str(exc)
        return result
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        result.update(status='rejected', reason=str(exc) if type(exc) is ValueError
                      else 'Source consistency, YAML or scope check failed')
        return result
    try:
        scanner = scanner_path(root, executable)
        snapshots = []
        with tempfile.TemporaryDirectory(prefix='sentinel-validation-') as temp:
            for label, content in [('before', raw), ('after', edited.encode())]:
                directory = Path(temp) / label
                destination = directory / path
                destination.parent.mkdir(parents=True)
                destination.write_bytes(content)
                result['attempts'] += 1
                snapshots.append(findings(scan(scanner, directory), directory, path.as_posix()))
        before, before_targets, version = snapshots[0]
        after, after_targets, after_version = snapshots[1]
        result.update(scanner_version=version, before_findings=before.total(),
                      after_findings=after.total(), new_findings=(after - before).total())
        target = json.dumps(packet['evidence'][0]['yaml_path'])
        if version != after_version:
            raise ComparisonUnsupported('Scanner version changed between snapshots')
        result['target_removed'] = before_targets[target] > 0 and after_targets[target] == 0
        if before_targets[target] == 0:
            result.update(status='rejected', reason='Fresh baseline did not confirm the targeted finding')
        elif after_targets[target] > 0:
            result.update(status='rejected', reason='Targeted finding remains after the repair')
        elif after - before:
            result.update(status='rejected', reason='New or strengthened findings appeared after repair')
        else:
            result.update(status='validated', reason='Target removed with no new scanner findings')
            result['checks'].append('Two bounded offline scans compared by YAML route and multiplicity')
    except ComparisonUnsupported as exc:
        result.update(status='unsupported', reason=str(exc))
    except (ScannerUnavailable, OSError) as exc:
        result.update(status='unavailable', reason=str(exc) if isinstance(exc, ScannerUnavailable)
                      else 'Scanner environment unavailable')
    return result
