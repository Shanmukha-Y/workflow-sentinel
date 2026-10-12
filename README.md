# Workflow Sentinel

Workflow Sentinel turns [zizmor](https://docs.zizmor.sh/) findings into JSON reports for reviewing GitHub Actions workflows. It connects each finding to local source evidence and adds remediation guidance with links to the relevant documentation.

It currently supports three zizmor rules:

- `template-injection`: untrusted expressions used in script contexts.
- `excessive-permissions`: overly broad workflow or job token permissions.
- `dangerous-triggers`: privileged triggers that need closer review, including possible untrusted checkout.

Reports include review decisions, source ranges, excerpts, file hashes, and guidance. Workflow context shows triggers, permission declarations, the affected job and step, expression references, and checkout references, with citations to their YAML locations. Each entry includes a short investigation trace. Findings with missing evidence or unsupported rules are marked `abstain` with a reason. An optional repair preview produces a constrained diff for supported Bash injection patterns.

## Install

Requires Python 3.11 or later. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Quick start

Try the included example:

```sh
workflow-sentinel \
  --sarif fixtures/vulnerable/findings.sarif \
  --repo fixtures/vulnerable > report.json
```

This produces three entries: an expression embedded in a shell command, `write-all` token permissions, and a privileged trigger with a pull request checkout. This example uses hand-authored SARIF to demonstrate the report format. See [the example report](examples/offline-report.json) for the full output.

For your own repository, [install zizmor](https://docs.zizmor.sh/installation/) and generate SARIF first:

```sh
cd /path/to/repo
zizmor --offline --format=sarif . > findings.sarif
workflow-sentinel --sarif findings.sarif --repo . > report.json
```

Run zizmor from the repository root so source paths are relative to `--repo`. Sentinel accepts SARIF 2.1.0 with either the rule IDs listed above or their `zizmor/`-prefixed forms. Reports use the unprefixed IDs for supported rules. It writes JSON to stdout and errors to stderr. Exit code `0` means the report was generated, including any findings; `2` indicates invalid input.

## Repair previews

```sh
workflow-sentinel \
  --sarif fixtures/repairable/findings.zizmor-1.30.1.sarif \
  --repo fixtures/repairable \
  --preview-repairs > preview.json
```

For a supported Bash step, the preview moves an untrusted expression into `env` and uses a quoted variable in the script:

```yaml
env:
  SENTINEL_INPUT: ${{ github.event.pull_request.title }}
run: |
  printf '%s\n' "$SENTINEL_INPUT"
```

The JSON `repair` entry contains a unified diff, the original and proposed file hashes, and validation notes. Review the diff and verify the original hash before applying it. Sentinel leaves the source unchanged. See [the example preview](examples/repair-preview.json).

Previews currently support one literal `printf '%s'` or `printf '%s\n'` command in a `run: |` block with explicit `shell: bash` and a matching SARIF snippet or source hash. The expression must be a supported PR/issue title or body reference, or `github.head_ref`. Existing environment declarations, container/default execution settings, extra commands, redirections, and ambiguous contexts produce a repair abstention. Permission reductions need explicit validated requirements and are not implemented; trigger and checkout changes remain report-only.

## Static validation

With a trusted native zizmor **1.30.1** binary installed outside the repository being reviewed:

```sh
workflow-sentinel \
  --sarif fixtures/repairable/findings.zizmor-1.30.1.sarif \
  --repo fixtures/repairable \
  --validate-repairs \
  --scanner /absolute/path/to/zizmor > validation.json
```

`--validate-repairs` includes repair previews and checks each eligible candidate against current source. It reconstructs the allowed edit, verifies hashes and YAML, then scans the original and candidate in separate temporary directories. Only the selected workflow is copied. Source files remain unchanged.

The `static_validation` entry reports one of four outcomes:

- `validated`: a fresh scan confirmed the target finding; the candidate removes it without new or strengthened findings.
- `rejected`: source or edit checks failed, the target remains, or the scanner comparison found a regression.
- `unsupported`: the repair or comparison falls outside the supported scope.
- `unavailable`: the scanner is missing, failed, timed out, returned malformed output, or reached a resource limit.

Comparison uses rule, severity, confidence, YAML location and finding multiplicity, so inserted lines do not create false regressions. Validation covers one workflow, not the entire repository. Missing local actions and dynamic/nonstandard action references are unsupported.

Scanner arguments are fixed: offline SARIF, strict collection, regular persona, no configuration loading or ignore rules. The scanner receives a minimal environment. Each call has a 15-second timeout, a 1 MB stdout limit and a 64 KB stderr limit. At most two candidates are checked per report, with two calls each and no retries. Other scanner versions and script wrappers are currently unsupported. If `--scanner` is omitted, Sentinel looks for an installed `zizmor` binary on PATH.

A validated result is a static check, not a security guarantee; review the diff before applying it. See [the example validation report](examples/static-validation.json).

## Advisory adapter replay

The optional adapter interpreter accepts structured requests to inspect a finding's verified
local evidence, request a constrained proposal, run static validation, or abstain. The included
scripted transport replays JSON responses offline; it is a reproducible interface demo, not a
live model. Packet indices refer to the deterministic report's sorted `packets` array.

```sh
workflow-sentinel \
  --sarif fixtures/repairable/findings.zizmor-1.30.1.sarif \
  --repo fixtures/repairable \
  --agent-script examples/agent-script.json \
  --scanner /absolute/path/to/zizmor > agent-report.json
```

The example requests evidence, a proposal, validation, then completion. With the supported
scanner it produces an advisory `review` selection and a static validation result. Without
`--scanner` it abstains at validation; this mode never discovers a scanner on PATH. Existing
CLI behavior remains the default when `--agent-script` is absent.

The [request schema](schemas/agent-script.schema.json) permits only `evidence`, `propose`,
`validate`, `finish` with an integer packet index, or `abstain` alone. Unknown fields, paths,
commands, arbitrary patch text, and free-form rationale are rejected. Evidence selects only
previously resolved packets; proposals require a prior evidence request and come from the
existing deterministic repair policy. Proposed repairs cannot complete without successful
static validation. Neither replay nor validation applies a patch to the original repository.

There are at most eight responses, 4 KB per response, 64 KB of cumulative tool observations,
and two validation pairs without retries. A 65-second loop deadline is checked between turns;
individual scanner subprocesses retain their 15-second deadline. Initial investigation retains
its existing resource bounds. Scripts are read under the CLI's 1 MB input cap. Traces contain
only fixed action/status values and turn numbers; evidence/report excerpts remain untrusted
source content and may contain secrets. The result is an `agent-1.0` envelope around the
unchanged deterministic report format.

See [the adapter contract and live-provider gates](docs/ADAPTER.md). No provider transport is
included yet. Scripted tests exercise policy enforcement, not model reasoning, prompt-injection
resistance, or live-model quality.

## Limitations

A `review` decision means the finding resolved to workflow context, not that exploitability was confirmed. Conditions and expressions are recorded as declarations; Sentinel does not evaluate them or determine the permissions a job needs. Shell context currently covers explicit step-level settings. Sentinel does not independently scan workflows, and an empty report does not establish security.

Use the same checkout that was scanned. Supplied SHA-256 hashes and source snippets are checked against local content; mismatches produce abstentions. Reports label provenance as `hash-matched`, `snippet-matched`, or `unverified`. A matching snippet checks a fragment, and a supplied hash is not an authenticated scan revision. Reports include source excerpts, so check for sensitive content before sharing.

Investigation reads are capped at 32 files and 4 MB total, with a 1 MB limit per file, 1,000 findings, and 10 locations per finding. YAML structure and context have size and depth limits. Ambiguous locations, duplicate keys, anchors, aliases, explicit tags, remote paths, symlinks, and SARIF URI base references produce abstentions. Source citations use one-based lines and Unicode code-point columns. Repository reads require POSIX directory-descriptor support (Linux or macOS). The [schemas](schemas) describe the accepted input subset and report format (`schema_version: 1.3`).

## Evaluation

A frozen synthetic suite checks triage, repair eligibility, citation/source consistency and static validation. The audited first-use subset matched 15/15 policy labels, with 5/5 exact candidate diffs and 4/4 real scanner comparisons. These are narrow policy checks, not vulnerability-detection or security guarantees. See [evaluation methodology, original results and corrections](evaluation/README.md).

```sh
python evaluation/run.py --scanner /absolute/path/to/zizmor --output /tmp/sentinel-evaluation-regression.json
```

## Development

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
ruff check .
mypy src
```

See [ROADMAP.md](ROADMAP.md) for planned investigation, repair, and validation work.
