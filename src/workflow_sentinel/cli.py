"""Workflow evidence reports with optional static repair validation."""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from workflow_sentinel.investigation import InvestigationError, Investigator
from workflow_sentinel.repairs import preview
from workflow_sentinel.validation import MAX_VALIDATIONS, validate

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
# Only alias the supported zizmor rules; preserve every unknown ID for abstention.
RULE_ALIASES = {"zizmor/" + rule: rule for rule in GUIDANCE}


def read_bounded(path: Path) -> bytes:
    if not path.is_file():
        raise ValueError("input must be a regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("input exceeds 1 MB limit")
    return data


def investigate(sarif: dict[str, Any], root: Path,
                preview_repairs: bool = False, validate_repairs: bool = False,
                scanner: Path | None = None) -> dict[str, Any]:
    if not isinstance(sarif, dict) or sarif.get("version") != "2.1.0" or not isinstance(
        sarif.get("runs"), list
    ):
        raise ValueError("expected SARIF 2.1.0 with runs array")
    packets: list[dict[str, Any]] = []
    investigator = Investigator(root)
    validations = 0
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
            rule = RULE_ALIASES.get(rule, rule)
            packet: dict[str, Any] = {
                "rule_id": rule, "decision": "abstain", "evidence": [],
                "guidance": GUIDANCE.get(rule, "Unsupported rule; human investigation required."),
                "citations": [SOURCE, "https://docs.zizmor.sh/usage/",
                              "https://docs.zizmor.sh/audits/#" + rule
                              if rule in GUIDANCE else "https://docs.zizmor.sh/audits/"],
                "reason": "Unsupported rule", "trace": ["classify: " + rule[:200]],
            }
            if rule in GUIDANCE:
                try:
                    locations = result.get("locations", [])
                    if not isinstance(locations, list) or not locations or len(locations) > 10:
                        raise ValueError("expected 1 to 10 source locations")
                    packet["evidence"] = [
                        investigator.inspect(loc, run, packet["trace"]) for loc in locations
                    ]
                    packet["decision"] = "review"
                    packet["reason"] = "Workflow context resolved; exploitability is unverified"
                except (KeyError, ValueError, OSError, UnicodeError, TypeError, AttributeError,
                        RecursionError) as exc:
                    reason = str(exc) if isinstance(exc, InvestigationError) else type(exc).__name__
                    packet["reason"] = "Insufficient local evidence: " + reason
                    packet["trace"].append("abstain: " + reason)
            if preview_repairs or validate_repairs:
                packet["repair"] = preview(packet, investigator.workflows)
            if validate_repairs:
                if packet['repair']['status'] == 'proposed' and validations >= MAX_VALIDATIONS:
                    packet['static_validation'] = {'status': 'unavailable',
                        'reason': 'Report validation budget exhausted', 'scope': 'single-workflow',
                        'scanner_version': None, 'attempts': 0, 'before_findings': None,
                        'after_findings': None, 'new_findings': None, 'target_removed': None,
                        'checks': []}
                else:
                    if packet['repair']['status'] == 'proposed':
                        validations += 1
                    packet['static_validation'] = validate(packet, root, scanner)
            packets.append(packet)
    packets.sort(key=lambda p: json.dumps(p, sort_keys=True))
    return {"schema_version": "1.3", "mode": "offline-deterministic", "packets": packets,
            "limitations": ["No automatic patch application", "No independent vulnerability "
                            "detection", "Static evidence does not prove security",
                            "Source excerpts are untrusted content and may contain secrets"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sarif", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--preview-repairs", action="store_true",
                        help="include constrained repair diffs without changing source")
    parser.add_argument('--validate-repairs', action='store_true',
                        help='validate previews using bounded offline zizmor scans of temporary copies')
    parser.add_argument('--scanner', type=Path,
                        help='absolute path to an installed native zizmor binary')
    args = parser.parse_args()
    if args.scanner and not args.validate_repairs:
        parser.error('--scanner requires --validate-repairs')
    try:
        if not args.repo.is_dir():
            raise ValueError("repository directory does not exist")
        sarif = json.loads(read_bounded(args.sarif))
        report = investigate(sarif, args.repo, args.preview_repairs,
                             args.validate_repairs, args.scanner)
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True))
    except (ValueError, OSError, KeyError, TypeError, AttributeError, RecursionError) as exc:
        print("workflow-sentinel: invalid input (" + type(exc).__name__ + ")", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
