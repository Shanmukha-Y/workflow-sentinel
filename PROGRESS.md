# Progress

## 2026-10-08 — Day one

Implemented deterministic Python CLI, bounded source reads, confined paths, hashes, citations,
abstentions, schemas, synthetic fixtures, tests and CI. No patches, agent tool planning,
YAML-aware investigation or live model integration yet. Synthetic tests are not real-world
security performance measurements. Launch handoff records validation and remote outcomes.

Local validation: 9 unit tests passed; Ruff 0.14.0 passed; strict mypy 1.18.2 passed
(Python 3.12.9). Vulnerable fixture produced three review packets; mitigation fixture produced
zero. Schema validation is included in tests. Pinned CI action SHAs verified against upstream
v4.2.2 checkout and v5.6.0 setup-python tags. No target workflows or scripts were executed.

## 2026-10-08 America/New_York — Evidence investigation

Continues the initial build completed October 7 evening Eastern (October 8 UTC).
Prior follow-ups rewrote the README and added exact aliases for supported zizmor-prefixed IDs
(commit 9e7f4cc); those changes are already complete and should not be repeated.

Added bounded YAML-node investigation with job/step paths, trigger and permission declarations,
conditions, explicit step shell settings, run/step-env expression references, checkout references,
and precise source citations. Workflow-level findings inspect checkout declarations across jobs.
Artifact indices and supplied SHA-256 hashes are supported; snippets are checked against the
located source. Mismatches and ambiguous metadata abstain with a readable trace. Provenance
labels distinguish a hash match, a fragment match and unverified input. Reports now use schema 1.1.

Repository reads use directory descriptors and reject symlinks and special files. Limits include
32 files/4 MB total, 1 MB per file, 5,000 YAML nodes, depth 32, 30 jobs and 100 steps per job.
No YAML constructors are invoked; anchors, aliases, explicit tags, merges, duplicate keys and
multiple documents abstain. Unicode columns are converted when SARIF declares their unit;
ambiguous astral-Unicode positions without a column kind abstain.

Validation: 29 unit tests passed, including actual zizmor 1.30.1 SARIF, stale snippets/hashes,
multiline source, job permission overrides, artifact indexing, resource bounds, adversarial YAML,
Unicode positions and file confinement. Ruff and strict mypy passed. Fresh static zizmor output
was exercised through the CLI. CI/commit results are in the launch handoff.

Next: constrained repair previews for injection and permissions; untrusted checkout stays
report-only. Preserve context/provenance checks and test repair refusal on ambiguity. Remaining
limits: no authenticated scan revision, runtime expression evaluation, required-scope inference,
workflow/job default-shell resolution, or full YAML feature support. A snippet match only checks
a fragment. Do not report the entire security investigation or validation roadmap as complete.

## 2026-10-09 America/New_York — Constrained repair previews

Started from verified faf9b97 with a clean working tree and matching private remote. Added
`--preview-repairs` and schema 1.2. Eligible Bash steps move one known untrusted expression from
a literal `printf` command into a new step env variable and replace it with a quoted expansion.
The preview contains a unified diff and base/proposed SHA-256 hashes. No automatic application.

Eligibility requires a source-resolved injection finding, exactly one location, matching source
snippet/hash, explicit `shell: bash`, a conventional workflow path and LF source. Refuse existing
env declarations, variable collisions, containers/defaults, unsupported expressions, extra
commands, redirects, alternate shell/header forms, stale evidence and already-fixed scripts.
Reparse the candidate and compare the entire YAML tree: only the selected run and new env entry
may differ. Permissions are never reduced without explicit validated requirements; that repair
path is not implemented. Dangerous triggers/untrusted checkout remain report-only.

Validation: 39 unit tests, Ruff and strict mypy passed. Tests check disposable diff application,
source immutability, hashes, exact expected AST change, opt-in CLI behavior and refusal cases.
Real zizmor 1.30.1 on the isolated repair fixture reported one template-injection finding before
and zero findings after the preview diff was applied as data to a disposable copy. No target
script was executed. This single-fixture result is not held-out performance or proof of security.
Captured scanner data, expected fixed YAML and example preview are committed for reproducibility.

Next session: bounded static validation loop, capped retries, robust diff/base-hash checks and
scanner-result comparison. Preserve natural README style and private visibility. Do not repeat
the completed evidence investigation or compatibility work. Remaining limits: very narrow
script support, no permission requirement interface, no authenticated scan revision, and no
general semantic-equivalence or security proof. CI/remote results are in the increment handoff.

## 2026-10-10 America/New_York — Static validation loop

Started from verified 80a8c359 with a clean checkout and matching private remote. Added opt-in
`--validate-repairs` and optional absolute `--scanner` path. Reports now use schema 1.3 and
separate validated, rejected, unsupported and unavailable outcomes. Recheck the current source
hash, reconstruct the exact allowlisted preview and reparse YAML before launching the scanner.

Copy only the selected workflow into separate before/after temporary roots. Invoke an installed
native zizmor binary outside the target repository with fixed offline SARIF arguments, strict
collection, regular persona, no config or ignores, and a scrubbed environment. Never execute
workflow run blocks, target scripts or commands from source. Local/dynamic/nonstandard action
references are unsupported because their context is absent from these isolated snapshots.

Limits: two candidates per report, two scans per eligible candidate, no retries, 15 seconds per
scan, 1 MB stdout and 64 KB stderr. Kill the scanner process group on a timeout/output breach.
Comparison requires valid zizmor 1.30.1 SARIF with successful invocations and resolvable source
evidence. Compare rule/level/severity/confidence and YAML routes with duplicate multiplicity,
not raw line numbers. Confirm the target in the fresh baseline, require its removal, and reject
new or strengthened findings. Unsupported formats/versions are distinct from scanner failures.

Validation: 54 unit tests passed; Ruff and strict mypy passed. Tests cover isolated copies and
cleanup, source/diff tampering, target absence/persistence, regressions and strengthened levels,
shifted lines, duplicate counts, malformed SARIF, missing/unsafe scanner paths, fixed argv and
environment, timeout group termination, output limits, launch/exit failures and report budgets.
Live opt-in CLI validation with zizmor 1.30.1 confirmed 1 finding before, 0 after, no new findings,
and an unchanged original workflow. This is one fixture, not general measured effectiveness.

Next session: freeze adversarial/held-out evaluation data and measure coverage, precision,
abstention and repair/validation outcomes honestly. Keep repair support narrow and checkout
report-only. Remaining limits: single-workflow comparisons, one supported scanner version, no
permission-requirement interface, no authenticated scan revision or runtime/security proof.
Native scanner installation is trusted; this is process bounding, not an OS security sandbox.
CI and exact remote commit results are in the increment handoff.
