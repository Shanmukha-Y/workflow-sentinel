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
