"""Bounded repository reads and YAML-node investigation; no target code execution."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlsplit

import yaml
from yaml.events import AliasEvent, MappingEndEvent, MappingStartEvent
from yaml.events import ScalarEvent, SequenceEndEvent, SequenceStartEvent
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

MAX_BYTES = 1_000_000
MAX_TOTAL_BYTES = 4_000_000
MAX_FILES = 32
MAX_NODES = 5_000
MAX_DEPTH = 32
MAX_STEPS = 100
MAX_JOBS = 30
EXPRESSION = re.compile(r"\$\{\{(.{1,500}?)\}\}", re.DOTALL)
PathParts = tuple[str | int, ...]


class InvestigationError(ValueError):
    """A stable, non-source-containing reason suitable for a review trace."""


class RepositoryReader:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.cache: dict[str, bytes] = {}
        self.total = 0
        self.attempts = 0

    def read(self, relative: Path) -> bytes:
        key = relative.as_posix()
        if key in self.cache:
            return self.cache[key]
        if self.attempts >= MAX_FILES:
            raise InvestigationError("repository file budget exceeded")
        self.attempts += 1
        # Walk via directory descriptors so a replaced symlink cannot redirect a read.
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            for part in relative.parts[:-1]:
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            file_fd = os.open(relative.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                              dir_fd=descriptor)
            before = os.fstat(file_fd)
            if not stat.S_ISREG(before.st_mode):
                os.close(file_fd)
                raise InvestigationError("source is not a regular file")
            if before.st_size > MAX_BYTES or self.total + before.st_size > MAX_TOTAL_BYTES:
                os.close(file_fd)
                raise InvestigationError("source size or repository byte budget exceeded")
            with os.fdopen(file_fd, "rb") as stream:
                raw = stream.read(min(MAX_BYTES, MAX_TOTAL_BYTES - self.total) + 1)
                self.total += len(raw)
                after = os.fstat(stream.fileno())
                if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns
                ):
                    raise InvestigationError("source changed during read")
        finally:
            os.close(descriptor)
        if len(raw) > MAX_BYTES:
            raise InvestigationError("source exceeds 1 MB limit")
        if self.total > MAX_TOTAL_BYTES:
            raise InvestigationError("repository byte budget exceeded")
        self.cache[key] = raw
        return raw


def relative_path(artifact: dict[str, Any]) -> Path:
    uri = artifact.get("uri")
    if not isinstance(uri, str) or urlsplit(uri).scheme or urlsplit(uri).netloc:
        raise InvestigationError("source path must be repository-relative")
    if artifact.get("uriBaseId"):
        raise InvestigationError("SARIF URI base references are unsupported")
    path = Path(unquote(uri))
    if path.is_absolute() or ".." in path.parts or not path.name:
        raise InvestigationError("source path escapes repository")
    if path.suffix not in {".yml", ".yaml"}:
        raise InvestigationError("source is not a YAML file")
    return path


def mapping(node: Node) -> dict[str, Node]:
    if not isinstance(node, MappingNode):
        raise InvestigationError("expected YAML mapping")
    result: dict[str, Node] = {}
    for key, value in node.value:
        if not isinstance(key, ScalarNode) or key.value == "<<":
            raise InvestigationError("complex YAML keys and merges are unsupported")
        if key.value in result:
            raise InvestigationError("duplicate YAML key")
        result[key.value] = value
    return result


def compose(text: str) -> MappingNode:
    count = depth = 0
    try:
        for event in yaml.parse(text, Loader=yaml.BaseLoader):
            if isinstance(event, AliasEvent) or getattr(event, "anchor", None):
                raise InvestigationError("YAML anchors and aliases are unsupported")
            if getattr(event, "tag", None):
                raise InvestigationError("explicit YAML tags are unsupported")
            if isinstance(event, (MappingStartEvent, SequenceStartEvent, ScalarEvent)):
                count += 1
                if count > MAX_NODES:
                    raise InvestigationError("YAML node budget exceeded")
            if isinstance(event, (MappingStartEvent, SequenceStartEvent)):
                depth += 1
                if depth > MAX_DEPTH:
                    raise InvestigationError("YAML depth budget exceeded")
            if isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                depth -= 1
        node = yaml.compose(text, Loader=yaml.BaseLoader)
    except yaml.YAMLError as exc:
        raise InvestigationError("invalid YAML document") from exc
    if not isinstance(node, MappingNode):
        raise InvestigationError("workflow root must be a mapping")
    return node


@dataclass
class Workflow:
    path: str
    raw: bytes
    text: str
    root: MappingNode
    entries: list[tuple[PathParts, Node]]

    @classmethod
    def parse(cls, path: str, raw: bytes) -> Workflow:
        text = raw.decode("utf-8")
        if re.search(r"\r(?!\n)|[\x85\u2028\u2029\x0b\x0c]", text):
            raise InvestigationError("unsupported source newline convention")
        root = compose(text)
        entries: list[tuple[PathParts, Node]] = []

        def visit(node: Node, route: PathParts) -> None:
            entries.append((route, node))
            if isinstance(node, MappingNode):
                mapping(node)  # Reject duplicate keys everywhere, not just selected context.
                for key, value in node.value:
                    visit(key, (*route, cast(ScalarNode, key).value))
                    visit(value, (*route, cast(ScalarNode, key).value))
            elif isinstance(node, SequenceNode):
                for index, value in enumerate(node.value):
                    visit(value, (*route, index))

        visit(root, ())
        data = mapping(root)
        if "jobs" not in data:
            raise InvestigationError("YAML is not a workflow with jobs")
        mapping(data["jobs"])
        return cls(path, raw, text, root, entries)

    def cite(self, node: Node) -> str:
        return (f"{self.path}:{node.start_mark.line + 1}:{node.start_mark.column + 1}"
                f"-{node.end_mark.line + 1}:{node.end_mark.column + 1}")

    def locate(self, line: int, column: int | None) -> PathParts:
        point = (line - 1, (column or 1) - 1)
        routes = {
            route for route, node in self.entries if isinstance(node, ScalarNode)
            and ((node.start_mark.line <= line - 1 < node.end_mark.line
                  + (1 if node.end_mark.column > 0 else 0)) if column is None
                 else (node.start_mark.line, node.start_mark.column) <= point
                 < (node.end_mark.line, node.end_mark.column))
        }
        if len(routes) != 1:
            raise InvestigationError("source location has no unique YAML node")
        return next(iter(routes))

    def summary(self, route: PathParts) -> dict[str, Any]:
        data = mapping(self.root)
        citations: list[str] = []
        trigger = data.get("on")
        triggers: list[str] = []
        if trigger is not None:
            citations.append(self.cite(trigger))
            if isinstance(trigger, MappingNode):
                triggers = list(mapping(trigger))
            elif isinstance(trigger, SequenceNode):
                triggers = [scalar(n) for n in trigger.value]
            elif isinstance(trigger, ScalarNode):
                triggers = [trigger.value]
        if len(triggers) > 30:
            raise InvestigationError("trigger context budget exceeded")
        job_id = route[1] if len(route) >= 2 and route[0] == "jobs" else None
        jobs = mapping(data["jobs"])
        if len(jobs) > MAX_JOBS:
            raise InvestigationError("job context budget exceeded")
        job = mapping(jobs[str(job_id)]) if job_id is not None else {}
        step_index = (route[3] if len(route) >= 4 and route[2] == "steps"
                      and isinstance(route[3], int) else None)
        steps_node = job.get("steps")
        steps: list[Node] = []
        if steps_node is not None:
            if not isinstance(steps_node, SequenceNode) or len(steps_node.value) > MAX_STEPS:
                raise InvestigationError("unsupported steps or step context budget exceeded")
            steps = steps_node.value
        selected = mapping(steps[step_index]) if step_index is not None else {}
        permission = job.get("permissions", data.get("permissions"))
        permission_source = ("job" if "permissions" in job else
                             "workflow" if "permissions" in data else "repository-default")
        permission_value: str | dict[str, str] | None = None
        if permission is not None:
            permission_value = (scalar(permission) if isinstance(permission, ScalarNode)
                                else {k: scalar(v) for k, v in mapping(permission).items()})
            citations.append(self.cite(permission))
        checkouts: list[dict[str, Any]] = []
        inspected_jobs = {str(job_id): jobs[str(job_id)]} if job_id is not None else jobs
        for checkout_job, job_node in inspected_jobs.items():
            checkout_steps = mapping(job_node).get("steps")
            if checkout_steps is None:
                continue
            if (not isinstance(checkout_steps, SequenceNode)
                    or len(checkout_steps.value) > MAX_STEPS):
                raise InvestigationError("unsupported steps or step context budget exceeded")
            for index, step in enumerate(checkout_steps.value):
                step_data = mapping(step)
                uses = step_data.get("uses")
                if uses is not None and scalar(uses).startswith("actions/checkout@"):
                    options = mapping(step_data["with"]) if "with" in step_data else {}
                    checkouts.append({"job": checkout_job, "step_index": index,
                                      "uses": scalar(uses),
                                      "ref": scalar(options["ref"]) if "ref" in options else None,
                                      "repository": scalar(options["repository"])
                                      if "repository" in options else None,
                                      "citation": self.cite(step)})
                    if len(checkouts) > 40:
                        raise InvestigationError("checkout context budget exceeded")
        run = selected.get("run")
        expressions = [] if run is None else references(scalar(run))
        env_references: dict[str, list[str]] = {}
        if "env" in selected:
            for name, value in mapping(selected["env"]).items():
                refs = references(scalar(value))
                if refs:
                    env_references[name] = refs
                    citations.append(self.cite(value))
        for group, key in [(job, "if"), (selected, "if"), (selected, "run"),
                           (selected, "shell")]:
            if key in group:
                citations.append(self.cite(group[key]))
        context = {"job": job_id, "step_index": step_index, "triggers": triggers,
                "permissions": {"source": permission_source, "declaration": permission_value},
                "job_if": scalar(job["if"]) if "if" in job else None,
                "step_if": scalar(selected["if"]) if "if" in selected else None,
                "shell": scalar(selected["shell"]) if "shell" in selected else None,
                "run_expressions": expressions, "env_expressions": env_references,
                "checkouts": checkouts, "citations": sorted(set(citations))}
        if len(json.dumps(context)) > 16_000:
            raise InvestigationError("serialized context budget exceeded")
        return context


def scalar(node: Node) -> str:
    if not isinstance(node, ScalarNode):
        raise InvestigationError("context value is not a scalar")
    if len(node.value) > 10_000:
        raise InvestigationError("context scalar budget exceeded")
    return str(node.value)


def references(value: str) -> list[str]:
    return sorted(set(match.strip() for match in EXPRESSION.findall(value)))


def source_column(text: str, column: Any, kind: Any) -> int:
    if type(column) is not int or column < 1:
        raise InvestigationError("invalid SARIF source column")
    if kind not in {None, "unicodeCodePoints", "utf16CodeUnits"}:
        raise InvestigationError("unsupported SARIF column kind")
    if kind is None and any(ord(char) > 0xFFFF for char in text):
        raise InvestigationError("SARIF column kind required for astral Unicode")
    if kind != "utf16CodeUnits":
        return int(column)
    units = 1
    for index, char in enumerate(text):
        if units == column:
            return index + 1
        units += 2 if ord(char) > 0xFFFF else 1
    if units == column:
        return len(text) + 1
    raise InvestigationError("SARIF column is outside a Unicode character boundary")


class Investigator:
    def __init__(self, root: Path) -> None:
        self.reader = RepositoryReader(root)
        self.workflows: dict[str, Workflow] = {}

    def inspect(self, location: dict[str, Any], run: dict[str, Any],
                trace: list[str]) -> dict[str, Any]:
        physical = location["physicalLocation"]
        artifact = physical["artifactLocation"]
        artifacts = run.get("artifacts", [])
        if not isinstance(artifacts, list) or len(artifacts) > 1000:
            raise InvestigationError("invalid or oversized SARIF artifacts array")
        metadata: dict[str, Any] = {}
        if "index" in artifact:
            index = artifact["index"]
            if type(index) is not int or not 0 <= index < len(artifacts):
                raise InvestigationError("invalid SARIF artifact index")
            metadata = artifacts[index]
            indexed = metadata["location"]
            if "uri" in artifact and relative_path(artifact) != relative_path(indexed):
                raise InvestigationError("SARIF artifact path disagrees with index")
            artifact = {**indexed, **artifact}
        path = relative_path(artifact)
        trace.append("resolve: repository-relative YAML path")
        if "index" not in artifact:
            matches = []
            for item in artifacts:
                if not isinstance(item, dict) or not isinstance(item.get("location"), dict):
                    continue
                try:
                    if relative_path(item["location"]) == path:
                        matches.append(item)
                except (ValueError, TypeError):
                    continue  # Unrelated external artifacts never supply local evidence.
            if len(matches) > 1:
                raise InvestigationError("ambiguous SARIF artifact metadata")
            if matches:
                metadata = matches[0]
        key = path.as_posix()
        if key not in self.workflows:
            self.workflows[key] = Workflow.parse(key, self.reader.read(path))
        workflow = self.workflows[key]
        trace.append("read: bounded repository snapshot; YAML structure parsed")
        lines = workflow.text.splitlines()
        region = physical["region"]
        line = region["startLine"]
        end_line = region.get("endLine", line)
        column = region.get("startColumn")
        end_column = region.get("endColumn", len(lines[end_line - 1]) + 1
                                if type(end_line) is int and 1 <= end_line <= len(lines) else 1)
        if type(line) is int and 1 <= line <= len(lines) and column is not None:
            column = source_column(lines[line - 1], column, run.get("columnKind"))
        if type(end_line) is int and 1 <= end_line <= len(lines) and "endColumn" in region:
            end_column = source_column(lines[end_line - 1], end_column, run.get("columnKind"))
        if (type(line) is not int or type(end_line) is not int
                or not 1 <= line <= end_line <= len(lines) or end_line - line > 50
                or (column is not None and (type(column) is not int
                    or not 1 <= column <= len(lines[line - 1]) + 1))
                or type(end_column) is not int
                or not 1 <= end_column <= len(lines[end_line - 1]) + 1
                or (line == end_line and column is not None and end_column < column)):
            raise InvestigationError("invalid or oversized SARIF source region")
        route = workflow.locate(line, column)
        trace.append("locate: unique YAML path identified")
        digest = hashlib.sha256(workflow.raw).hexdigest()
        provenance = "unverified"
        expected = metadata.get("hashes", {}).get("sha-256")
        if expected is not None:
            if not isinstance(expected, str) or expected.lower() != digest:
                raise InvestigationError("SARIF source hash mismatch")
            provenance = "hash-matched"
        snippet = region.get("snippet", {}).get("text")
        if snippet is not None:
            if not isinstance(snippet, str) or not snippet:
                raise InvestigationError("invalid SARIF source snippet")
            candidates = {lines[line - 1].strip(), "\n".join(lines[line - 1:end_line])}
            for candidate_route, node in workflow.entries:
                if candidate_route == route and isinstance(node, ScalarNode):
                    candidates.add(node.value)
                    candidates.add(workflow.text[node.start_mark.index:node.end_mark.index])
            if snippet not in candidates:
                raise InvestigationError("SARIF source snippet mismatch")
            if provenance == "unverified":
                provenance = "snippet-matched"
        trace.append("provenance: " + provenance)
        context = workflow.summary(route)
        trace.append("context: triggers, permissions, job and step declarations inspected")
        return {"path": key, "line": line, "column": column or 1, "end_line": end_line,
                "column_kind": "unicodeCodePoints",
                "end_column": end_column, "sha256": digest, "excerpt": lines[line - 1][:500],
                "yaml_path": list(route), "provenance": provenance, "context": context,
                "citation": f"{key}:{line}:{column or 1}-{end_line}:{end_column}"}
