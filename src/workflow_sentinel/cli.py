"""Offline triage only: no subprocess, network, YAML execution, or model calls."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

MAX_BYTES = 1_000_000
MAX_RESULTS = 1_000
SOURCE = "https://docs.github.com/en/actions/reference/security/secure-use"
GUIDANCE = {
    "template-injection": "Review attacker control and shell context. Consider an intermediate "
    "environment variable and quoted shell expansion; do not blindly rewrite expressions.",
    "excessive-permissions": "Determine the minimum permissions each job requires before "
    "reducing token permissions. Required scopes cannot be inferred from a finding alone.",
    "dangerous-triggers": "Report only: investigate privileged triggers and untrusted checkout. "
    "Do not automatically change triggers or checkout references.",
}


def read_bounded(path: Path) -> bytes:
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("input exceeds 1 MB limit")
    return data


def evidence(root: Path, location: dict[str, Any]) -> dict[str, Any]:
    physical = location["physicalLocation"]
    uri = physical["artifactLocation"]["uri"]
    if not isinstance(uri, str) or urlsplit(uri).scheme or urlsplit(uri).netloc:
        raise ValueError("only repository-relative paths are accepted")
    if physical["artifactLocation"].get("uriBaseId"):
        raise ValueError("uriBaseId resolution is not supported")
    relative = Path(unquote(uri))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("path escapes repository")
    target = (root / relative).resolve()
    target.relative_to(root.resolve())
    if target.suffix not in {".yml", ".yaml"}:
        raise ValueError("evidence must be a YAML workflow file")
    raw = read_bounded(target)
    lines = raw.decode("utf-8").splitlines()
    line = physical["region"]["startLine"]
    if type(line) is not int or not 1 <= line <= len(lines):
        raise ValueError("invalid source line")
    return {"path": relative.as_posix(), "line": line,
            "sha256": hashlib.sha256(raw).hexdigest(), "excerpt": lines[line - 1][:500]}


def investigate(sarif: dict[str, Any], root: Path) -> dict[str, Any]:
    if not isinstance(sarif, dict) or sarif.get("version") != "2.1.0" or not isinstance(
        sarif.get("runs"), list
    ):
        raise ValueError("expected SARIF 2.1.0 with runs array")
    packets: list[dict[str, Any]] = []
    for run in sarif["runs"]:
        if not isinstance(run, dict):
            raise ValueError("run must be an object")
        tool = run.get("tool")
        if not isinstance(tool, dict) or not isinstance(tool.get("driver"), dict):
            raise ValueError("tool driver must be an object")
        if tool["driver"].get("name") != "zizmor":
            raise ValueError("only zizmor runs are supported")
        results = run.get("results", [])
        if not isinstance(results, list):
            raise ValueError("results must be an array")
        for result in results:
            if not isinstance(result, dict):
                raise ValueError("result must be an object")
            if len(packets) >= MAX_RESULTS:
                raise ValueError("too many results")
            rule = result.get("ruleId", "unknown")
            if not isinstance(rule, str):
                raise ValueError("ruleId must be text")
            packet: dict[str, Any] = {
                "rule_id": rule, "decision": "abstain", "evidence": [],
                "guidance": GUIDANCE.get(rule, "Unsupported rule; human investigation required."),
                "citations": [SOURCE, "https://docs.zizmor.sh/usage/",
                              "https://docs.zizmor.sh/audits/#" + rule
                              if rule in GUIDANCE else "https://docs.zizmor.sh/audits/"],
                "reason": "Unsupported rule",
            }
            if rule in GUIDANCE:
                try:
                    locations = result.get("locations", [])
                    if not isinstance(locations, list) or not locations or len(locations) > 10:
                        raise ValueError("expected 1 to 10 source locations")
                    packet["evidence"] = [evidence(root, loc) for loc in locations]
                    packet["decision"] = "review"
                    packet["reason"] = "SARIF locations resolved; exploitability is unverified"
                except (KeyError, ValueError, OSError, UnicodeError, TypeError, AttributeError) as exc:
                    packet["reason"] = "Insufficient local evidence: " + type(exc).__name__
            packets.append(packet)
    packets.sort(key=lambda p: json.dumps(p, sort_keys=True))
    return {"schema_version": "1.0", "mode": "offline-deterministic", "packets": packets,
            "limitations": ["No live model reasoning or patches", "No independent vulnerability "
                            "detection", "Static evidence does not prove security",
                            "Source excerpts are untrusted content and may contain secrets"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sarif", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    try:
        if not args.repo.is_dir():
            raise ValueError("repository directory does not exist")
        report = investigate(json.loads(read_bounded(args.sarif)), args.repo)
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        print("workflow-sentinel: invalid input (" + type(exc).__name__ + ")", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
