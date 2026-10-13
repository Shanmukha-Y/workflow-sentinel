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

### October 13 follow-up — Authorized real local Qwen evaluation

User authorized pulling a reasonable-size latest Qwen model and running it through their
installed Ollama. Checked clean starting checkout at 2a7e591 and processes: no other evaluation
was running; existing Ollama 0.40.0 listened only on 127.0.0.1:11434. Hardware: M4 Max, 48 GiB
RAM, about 522 GiB free disk. Official Ollama/Qwen catalog showed Qwen3.8 as newest, smallest
quantized 27B option around 18 GB. Selected explicit qwen3.8:27b-q4_K_M, not larger precision
variants. Official pull completed with SHA verification: 17,741,872,132 bytes, digest
25b843619e944cd0ae6069f94ff4e5e26a16e109ccbc0a66a0f05979ed70098e. Unrelated installed models
and daemon/listener configuration were unchanged. Weights remain installed for the user.

Added native local Ollama adapter and explicit local evaluation CLI. Endpoint is fixed IPv4
loopback; proxies/redirects, cloud tags, missing/non-GGUF/remote models and arbitrary tools are
refused. Native tool outputs are checked locally; no strict-generation guarantee is assumed.
The existing deterministic interpreter/scorer labels and system instruction were unchanged.
Generation config fixed before execution: think=false, temperature 0, seed 0, context 8192,
num_predict 256, non-streaming, keep-alive 2m; existing per-call/session/case/aggregate caps.
Recorded per-attempt actions, fingerprints, timings/token counts and model metadata without
raw prose/error bodies, prompts, credentials or private local paths. Response parsing acceptance
is distinct from deterministic permission to run a requested tool.

First actual local run preserved separately from all mocks: 4/8 policy completions, all eight
attempted, 23 parseable responses, zero transport/protocol errors/skips, 58.98 seconds including
cold loading/metadata/static validation. Both supported repairs completed and passed actual
paired zizmor validation (four scanner calls). Stale-source/benign controls correctly abstained.
Three manual-review cases abstained rather than completing the labeled review; those failures
remain, despite being conservative. The exposed instruction case requested validation after a
refused proposal; the deterministic guard denied it with no scan/patch for that case. It failed.
No claim that the comment caused the behavior, and no injection-resistance/security guarantee.
All source bytes unchanged; primary citation checks 6/6, confirmed attack payload exposure 1/1.
Ollama reported 21,266 prompt and 554 generated tokens over 23 known-usage responses. During-run
sample reported 17,837,955,480 bytes residency at 8K context, not peak host/GPU memory. Hardware,
server version, config, digest, code hashes and first failures are recorded with checksums.

Validation: 104 unit tests, Ruff, strict mypy on nine modules, 38/38 deterministic regression,
8/8 mock oracle regression. Added offline replay of actual failed instruction-case requests to
verify the guard denies validation without invoking the scanner. No model/labels/prompt tuned,
no real run repeated to hide failures. Reviewed current artifacts/docs for secrets/private data;
no credential-pattern or private-home-path matches. Real results have no raw source/model prose
or auth material. Added LOCAL_MODEL.md and updated current release/threat/adapter documentation.

Local inference was authorized and has now been genuinely measured; OpenAI/cloud inference is
still unused/unapproved. No credential configuration/discovery/transmission, paid API commitment,
deployment or public/social release occurred. Local hardware/electricity cost was not measured.
Keep the repository private: four declared quality failures remain, along with consolidated
release demo and separate human release authorization. Recoverable transport integration worked;
remaining failures are retained model/controller outcomes, not relabeled successes. Exact private
remote SHA and CI result are in the follow-up handoff.

### October 13 follow-up — General contract fix and fresh synthetic check

Started from clean b4c0150 with matching private remote, no competing evaluation and loopback-only
Ollama. Traces established three conservative abstentions after repair refusals and one blocked
validation request after refusal. No transport/schema/budget errors caused these four failures.
The original shared instruction conflated insufficient evidence/validation with unsupported
repair, and tool descriptions did not describe manual-review completion. The controller and
scorer already distinguished these; original expectations and 4/8 archive remain unchanged.
Internal model causation/source-comment effects cannot be inferred from those traces alone.

General changes: explicit review versus repair semantics in shared instructions/descriptions;
host-derived observation policy/next actions; prerequisite-aware native tool advertisement with
eligible packet enums and returned-call checks. No case/category-specific routing or label lookup.
Unsupported automatic repair with verified review evidence can complete manual review, not a
patch/security verdict. Insufficient evidence/failed validation still abstains; abstention always
available. Original controller source/hash/scope/order/scanner/budget checks remain unchanged.
OpenAI receives clarified descriptions/policy but real cloud-model behavior is still untested.

Six fresh exact synthetic variants were frozen before any model execution (463697f). Manual
source review corrected the job-permission SARIF line/column before the first holdout run (d4cf925)
without altering source or expected outcome. Variants cover non-Bash shell, job permissions,
privileged checkout, two exposed instruction comments and mismatched snippet. Self-authored with
implementation knowledge and known categories, not blind/independent or real-world detection.
No holdout result was used for tuning, and later reuse must be regression evidence.

Actual local results with the same already-installed Qwen digest/generation caps:
- Original baseline: 4/8, 23 requests, 58.98s (preserved).
- Original eight as development regressions after contract change: 8/8, 23 requests, 111.86s;
  22,080 prompt/629 output tokens, 6/6 citations, one exposure; two paired scanner comparisons.
- Fresh first-use synthetic holdout: 6/6, 17 requests, 74.88s; 15,032 prompt/482 output tokens,
  5/5 citations, 2/2 exposures; no eligible repairs/scanner comparison in this manual-review/
  abstention holdout. No errors/skips/source changes in either new run.
Combined contract changes support the improvement but do not isolate wording versus tool
filtering or prove broad injection resistance. Runtime increased; no speedup/causal claim.

Added consolidated synthetic demo with review/preview/agent/static-validation/unchanged-hash
artifacts. Verified both real local Qwen demo and offline scripted mode; summary retained with
checksums. Output directory preflight occurs before any model/scanner work. CI runs the offline
demo only. 110 unit tests, Ruff, strict mypy on nine modules, 38/38 deterministic regression,
8/8 mock oracle and both demos pass. Tests retain baseline/holdout records and verify state,
packet enums, untrusted policy text, manual-only completion and failed-validation refusal.

Release docs updated to distinguish baseline, development and first-use evidence, disclose
pre-run fixture correction, tight guidance and missing independent/multi-finding/broad adversarial
model evaluation. All original archives/checksums preserved. Keep private pending human release
authorization and acceptance of the documented scope; do not force release. No model download,
paid/cloud inference, credential configuration/discovery/transmission, deployment or social
posting occurred. Exact remote commit/CI evidence is in the handoff.

### October 13 — Real three-model comparison and initial release audit

Publication was paused to incorporate the user's model-comparison and actual-results-only
requirements. Selected official local Q4_K_M models after rechecking M4 Max/48 GiB RAM and
505 GiB free disk: Qwen3.8 27.3B (17.74 GB already present), Gemma4 30.7B (20.39 GB), Mistral
Small 3.2 24.0B (15.18 GB). No enormous variant, cloud model, paid inference or credentials.
Downloaded two additional public registry weights; loaded only one model at a time.

Frozen shared instructions/tools/budgets/scoring/code and fresh synthetic inputs (0c9cdcc).
First actual attempt retained nine completed groups, Qwen/Gemma passes and Mistral failures,
then stopped before repeats on an immediate unload-confirmation race. Raw Mistral records
showed dropped native tool-call IDs and prose/malformed terminal replies. General ID propagation,
explicit terminal tool-only/zero-argument abstention wording for every model and bounded unload
waiting were fixed, checked against official Ollama 0.40 types. No per-model prompt/budget
relaxation or label change. Retained first attempt/source snapshots and froze new exact
revision-two synthetic inputs/common corrected protocol (735203a) before every model reran.

Final actual comparison: 90 cases, 251 inference requests, 12 groups, 839.59s including load/
host work. Prior eight are development and prior six exposed; fresh revision-two eight run
once as first exact-source exposure and again as exposed replication, with reversed model
order. Qwen/Gemma 30/30 each, fresh 8/8 twice; Mistral 20/30, fresh 6/8 twice. Its ten missing/
unstructured terminal tool responses remain failures, not inferred successful abstentions.
No disallowed requests or observed unauthorized validation/source mutation in 90 checked cases.
All actual bounded request/response bodies, timing/token counts, fingerprints and failed runs
retained; model digests stable. No mock transport enters comparison/performance tables.

Measured matched successful repair medians: Qwen19.92s, Gemma21.00s, Mistral6.20s. Prompt/output
counts all groups: 84,148/2,189;61,072/1,112;55,167/826; unknown usage zero. Cold unloaded-model
preload separate from warm tasks, not OS/file-cache cold. API size_vram max samples17.84/2.74/
15.90GB; Gemma's tiny counter is not whole-model memory. Separate sequential actual 16-token
unscored probe plus ps daemon/descendant RSS sums gave18.75/23.15/16.58GB post-inference.
Those are samples/shared-page-sensitive, not true GPU/host peaks. Memory telemetry caveat and
unequal size/native runtime/tokenizer/cache/background conditions are prominent in REPORT.md.
Small self-authored known-category inputs, guided tools and two fixed-setting repeats do not
prove broad model reliability, intelligence, real-world security or injection resistance.

Product audit found advertised scripted replay/mock SDK demos. Removed --agent-script and
canned product fallback; agent.run now requires an adapter and featured demo requires actual
local model plus native scanner. Test-only helpers and historical mock oracle artifacts moved
under tests with original bytes/checksums/history preserved, never performance evidence.
Synthetic input fixtures remain intentionally labeled, not real incidents. Unit controlled
transports remain for protocol/scoring/error-path verification; no blanket no-mocks claim.
Static example outputs regenerated from actual deterministic CLI/native scanner execution.

Added MIT project license/SPDX packaging and dependency inventory; no weights/native binaries/
third-party code vendored. Fixed source distribution missing demo/test assets, including hidden
workflow files and relocated archives. Clean noneditable install/pip check, source/wheel license
and payload checks, extracted-sdist tests,117 unit tests, Ruff, strict mypy9modules and38/38
actual static regression pass. Final featured demo genuinely invoked Qwen and scanner, validated
and preserved original hashes. No deployment or social posting; only a draft will be returned.

Corrected the redundant human-release gate: standing user authorization permits public visibility
when ready. Initial release is scoped to verified Qwen/Gemma paths and honest experimental
Mistral failures. Final audit covers current tree plus every reachable historical blob for
credentials/private paths/user identifiers; hardware records are generic, no hostnames/device IDs/
private directories/customer content. Commit identity is intentional public GitHub handle/noreply.
Final exact remote commit/CI and unauthenticated public-access verification follow in handoff;
visibility changes only after those readiness checks. No additional confirmation is needed unless
a tool itself blocks. Full history/result provenance is preserved, without rewriting away failures.
