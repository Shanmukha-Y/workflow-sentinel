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

## 2026-10-11 America/New_York — Frozen synthetic evaluation

Started from d2fc6c6 with a clean checkout and matching private remote. Froze 38 synthetic
source/SARIF cases and manually specified policy outcomes/candidate YAML before any run
(f0dc2df); corrected the echo SARIF source line during label review before execution (997b3c7).
No production module was changed or tuned on the suite. Development and first-use labels were
run separately. Original records and hashes are retained rather than overwritten.

A post-run audit excluded five holdout variants already exercised by earlier unit tests.
Official subsets: 18 development, 15 synthetic first-use holdout, 5 reused regressions. Original
raw holdout file still has its initial 20-case naming; AUDIT and evaluation README explain the
correction. Another instrumentation error counted one zero-attempt preflight refusal as a live
scanner comparison: audited holdout has 4/4 actual comparisons plus 1/1 unsupported preflight,
not the original raw 5/5 live count. The evaluator now attributes these correctly.

Results: development 18/18, audited first-use 15/15, reused regressions 5/5 policy matches.
First-use repair eligibility precision/recall 5/5 each; triage precision/recall 7/7 each;
9/14 repair abstentions; 35/35 citation records passing bounded source checks; 5/5 exact
candidate diffs; 15/15 original sources unchanged; 4/4 real scanner comparisons. Across all
cases: 6 actual paired comparisons (12 zizmor calls), 6 simulated scanner-fault checks and one
preflight-only refusal. No production outcome failures were observed. Cases cover malformed/
tampered evidence, source/YAML limits, unsupported Bash, report-only permissions/checkout,
benign controls, misleading instruction-like comments and scanner regressions.

Limitations: self-authored with implementation knowledge, synthetic, not independent/blind
or real-world security measurement. Some branches were known from existing unit tests.
Policy precision/recall do not measure vulnerability detection; exact golden candidate checks
do not prove runtime semantic equivalence/security. Instruction comments do not test a model.
First-use results must not be replaced with later regression results. Production file hashes
in original reports identify the evaluated baseline.

Added reproducible evaluator, integrity/attribution tests, original/audited/regression reports,
and methodology. Full unit suite now 58 tests; Ruff and strict production mypy passed. CI will
also run the full regression suite with pinned zizmor. Next: optional adapter feasibility and
contract design, retaining offline default, no paid calls/credentials and no broader tools.
Do not silently relabel known cases as held-out in future runs.

## 2026-10-12 UTC — Bounded advisory adapter replay

Started from clean 45d65aca; private remote matched. Added an opt-in scripted adapter interpreter
with structured evidence/propose/validate/finish/abstain requests. It selects only existing
bounded source evidence and invokes deterministic repair/validation policies. No arbitrary
paths, commands, patch text, response rationale, provider plugins or target scripts are accepted.
Prior evidence is required for proposals; proposed repairs require successful static validation
before completion. Terminal responses must be last. Missing scanner, invalid responses/order,
failed validation and exhausted budgets abstain. Scanner opt-in is explicit, never PATH discovery
in replay mode. The ordinary offline CLI/report format is preserved.

Added strict response fields/types and duplicate JSON field rejection, eight-turn and 4 KB
response limits, 64 KB observation limit, two-pair validation budget, 65-second between-turn
loop deadline and existing per-scanner timeouts. Fixed-value traces exclude raw response text;
source evidence/report excerpts are still sensitive untrusted data, not redacted. The initial
investigation retains its existing resource bounds. Included request schema, reproducible
script, CLI instructions and a provider feasibility/contract document.

Checks: 70 unit tests, Ruff and strict mypy on six production modules. Frozen full regression
rerun matched 38/38 policy labels (a regression, not new first-use evidence). Real zizmor 1.30.1
scripted demo returned review with validated target removal, using two scanner calls; source
was unchanged. CI includes the scripted real-scanner demo and existing regression suite.
No live provider, credential access, model request, paid commitment or target execution occurred.
Mocked responses test interpreter enforcement, not prompt-injection resistance or model quality.

Release gates: threat model, reproducible consolidated demo, measured scope/failures and manual
release draft. Live model capability remains absent: a future adapter requires official API
verification, explicit data/cost approval, hard network cancellation, sanitized errors and a
separate adversarial live-model evaluation. Keep that gap visible; this increment does not
fulfill a claim of live LLM reasoning. Permission repairs remain deferred and checkout report-only.
Exact-commit CI and private remote verification are recorded in the increment handoff.

### October 12 follow-up — Implemented OpenAI provider transport

The replay-only handoff did not fulfill the requested provider integration. Added an actual
opt-in OpenAI Responses adapter with an injected configured synchronous SDK client. Each model
turn requests one strict allowlisted function, receives the preceding verified tool observation,
and runs through the same deterministic policy. The adapter requires explicit source disclosure,
model and output-token cap; it constructs no credential-bearing clients and discovers no keys.
Official function-calling and SDK documentation were fetched before implementation; links and
the checked SDK versions are in docs/ADAPTER.md. Runtime SDK is an optional dependency.

The official SDK 3.29.0 was installed and exercised exclusively through httpx2 2.13.1 in-memory
MockTransport using a fixed non-credential placeholder and empty constructor environment. No
real credential was retrieved/transmitted/saved, no live API call or paid commitment occurred.
A reproducible mock-transport demo performs interactive observation roundtrips and real zizmor
validation of the existing synthetic fixture; output is labeled mock-openai-transport-advisory.

Added strict completion/tool-call checks, unique call IDs, bounded reasoning continuation,
64 KB history and 16 KB decoded-response caps, 64–512 output-token cap, eight-request limit,
SDK timeout/retries=0 and POSIX main-thread wall deadlines capped by remaining session budget.
Conflicting alarms/threads refuse; provider error bodies are not stored. Input/byte/token bounds
are not monetary budgets; decoded size caps are not preallocation caps; store=False is not a
retention promise. Trusted SDK/native code is not process-isolated; details are documented.

Verification: 78 unit tests pass, including real SDK mocked wire protocol, multi-turn requests,
HTTP 429 without retry, malformed/refused/incomplete response, extra/unsafe arguments, duplicate
JSON fields/call IDs, bounded inputs/output/calls, actual local timeout and restored signal timer.
Ruff, strict mypy (seven production modules) and diff whitespace checks pass. Full frozen suite
rerun matched 38/38 regression policy labels. Mock provider plus real scanner demo validated;
source was unchanged. CI includes both adapter demos. Staged credential-pattern review and
exact private remote/CI verification are in the follow-up handoff.

Provider implementation gap is closed; live-model capability validation remains a release gate.
No mocked outcome measures real reasoning, model effectiveness or prompt-injection resistance.
Public release remains gated on honest live capability evidence (separate data/spend approval),
threat model, reproducible consolidated demo, measured limitations and human release decision.

## 2026-10-13 UTC — Reproducible model evaluation and release gates

Started from clean f4a92d4; private remote matched, one checkout and no Git lock/concurrent
changes observed. Added a frozen eight-case synthetic model-policy harness using known
regression fixtures, explicit pre-run labels and hashes, independent candidate/source citation
checks, observed-tool requirements and explicit terminal response scoring. No first-use/held-out
or real-world detection claim is made. Cases cover two supported repairs, ambiguous Bash,
permissions, report-only checkout, stale evidence, benign control and actually exposed source
instructions. Exposure requires a subsequent successful request containing the observation.

The first mock execution scored 7/8 due to a scorer assumption that multiline citations store
multiline excerpts. Existing investigation stores the first line. Corrected the scorer and
added a regression without changing labels or investigation. Preserved the original failure
and subsequent regression with checksums; original local-only exposure attribution is also
clearly distinguished from the corrected confirmed-request metric. SDK policy-oracle result:
8/8 completions, 23 attempts, 6/6 citation records, 1/1 required payload exposures and two real
paired zizmor validations/four scanner calls. This is harness/integration verification, not
live-model reasoning or prompt-injection-resistance measurement. Sources stayed unchanged.

Aggregate caps: eight cases, four provider attempts/case, 32 reservations overall, 256 output
tokens/request (8,192 requested maximum) and 540-second batch deadline checked at case/request
boundaries. Scanner/initial investigation keeps its own limits rather than a batch interrupt.
Failures/unknown usage consume reservations; skipped/error cases remain denominator failures.
Always abstaining can pass at most 2/8. Each fresh client is closed, including error paths;
cleanup failures count as failures. Records exclude source excerpts, prompts, raw responses and
error bodies; exclusive output prevents replacing prior runs. Added sanitized provider usage
accounting: missing/invalid usage is unknown, not zero. Mock oracle records 23 unknown usages;
known token accounting and over-cap refusals are tested with synthetic usage metadata.

Checks: 96 unit tests; Ruff; strict mypy on eight modules; 38/38 deterministic regression labels;
real scanner mock-oracle demo. Added threat model, release-readiness review and clear user-run
live instructions. Audit inspected 62 current project files and 93 reachable historical blobs:
no credential-pattern matches, private home paths or sensitive filenames. Reviewed synthetic
artifacts and report minimization. This is a bounded repository audit, not a guarantee that all
possible secrets/private data are absent; ignored/outside credential stores were not searched.

No credential creation/configuration/discovery/transmission, paid/live API call, deployment,
public release or social posting occurred. Live pilot remains unapproved and unvalidated.
Proposed scope is the fixed eight cases/32 requests; a monetary ceiling cannot be substantiated
without a selected model/current pricing, disclosure and spend approval/enforcement. Current
model API authorization is zero spend. Release stays private pending actual capability/failure
and billing evidence, a consolidated reproducible demo and separate human release decision.
Exact private remote SHA and CI result are in the increment handoff.
