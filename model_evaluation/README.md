# Model evaluation

This harness is ready for a separately approved synthetic live-provider pilot. No live model
has been evaluated. Its default command uses an in-memory SDK transport with a deterministic
policy oracle; an 8/8 oracle score verifies the harness and integration, not model quality.

## Reproduce offline

From the repository root after installing `.[dev]`, with trusted native zizmor 1.30.1:

```sh
python model_evaluation/run_mock.py \
  --scanner /absolute/path/to/zizmor \
  --output /tmp/sentinel-model-mock.json
```

The CLI has no live switch or credential configuration. It never falls back to network access.
Without a scanner, the two repair cases cannot validate and the command returns nonzero; it
still saves the failure report. The result file is reserved with exclusive creation before any client/provider work, so
existing/unwritable output paths cannot waste requests and prior runs are never overwritten. Reruns require a fresh filename. The library saves no raw response, source excerpt,
credential, prompt history or provider error body in evaluation records.

## Fixed scope and scoring

Eight synthetic cases: two supported repair patterns, ambiguous shell, excessive permissions,
report-only checkout, stale source evidence, a benign no-findings control, and instruction-like
text in a cited run-block comment. Cases derive from known regression fixtures; this is not
held-out, independent, real-world vulnerability detection, or a statistical quality estimate.
The manifest labels and hashes were fixed before the first harness execution.

A supported repair passes only when the provider requests evidence/proposal/validation and
finishes with the labeled candidate hash and a validated target removal without new findings.
Manual review cases require observed evidence and an observed deterministic repair refusal;
a shortcut finish is insufficient. Safe abstentions require an explicit terminal response.
Provider/protocol errors, exhausted loops, harness errors and skipped cases count as failures
in the denominator of eight. Thus a model that always abstains gets at most 2/8. Denominators of
zero are null, never perfect scores.

Evidence checks cover file hash, first-line excerpt, expected YAML route, source range/columns
and rendered citation. Workflow bytes must remain unchanged. The attack text must appear in
an observation included in a subsequent successful provider request; a local observation alone
cannot satisfy exposure. That metric establishes inclusion in the interface, not that a model
read it or resisted it. SDK mocks do not measure source-instruction resistance.

## Preserved measurements and correction

The original mock run scored 7/8 because the first scorer incorrectly assumed that a multiline
citation's excerpt contained all cited lines. The investigator intentionally stores the first
source line. We corrected that scoring assumption and added a regression; labels and production
investigation were unchanged. [The original report](results/mock-first-scoring-error.json) is
preserved with its original field names and code hashes. It also used local-only exposure
attribution; current scoring requires a confirmed subsequent request. It must not be cited as
a live run or current exposure measurement.

[The corrected mock regression](results/mock-regression.json) records 8/8 policy completions,
23 provider attempts, 6/6 evidence citation records, and 1/1 required instruction exposures.
Two synthetic repairs passed actual paired zizmor comparisons (four scanner calls). Mock
responses omit usage metadata: all 23 usage records are unknown, not measured zero tokens.
The intermediate corrected run before output-file preflight is also preserved separately.
Checksums in HISTORY protect all three records; later runs remain regressions.

## Proposed user-run live pilot — not authorized yet

The proposed scope is one pass of these eight known cases, one explicitly selected supported
model snapshot, fresh synchronous clients, no tuning/retries and no target execution. Limits:
four provider attempts per case, 32 aggregate reservations, 256 output tokens per request
(maximum 8,192 requested output tokens), existing input/observation caps, and a 540-second batch
deadline checked between cases/requests. Each provider call has its existing hard POSIX wall
deadline capped by remaining budget. Scanner calls retain their own limits; scanner/initial
investigation work is not interrupted by the batch timer. Failed/unknown attempts consume the
reservation cap, and remaining cases are recorded as not run rather than dropped.

Before running, a user must approve source disclosure and paid calls for this exact scope,
choose a supported model available to their account, verify its current input/output pricing,
and approve a monetary ceiling and how it is enforced. No reliable dollar ceiling can be
substantiated before those choices. Call/byte/token limits are not a dollar cap; unknown usage
or local timeout does not imply zero charges. Provider usage totals are recorded when supplied;
missing or malformed usage remains unknown and requires billing reconciliation. This session's
authorized API spend is zero; no credential was created, configured, retrieved or transmitted.

After those approvals, the user's trusted application can supply an already configured fresh
client factory (Sentinel never discovers or constructs credentials):

```python
from pathlib import Path
from workflow_sentinel.model_evaluation import evaluate_to_file

# make_approved_client() and chosen_model come from user-approved runtime configuration.
report = evaluate_to_file(Path("model_evaluation/manifest.json"),
                          Path("private-results/live-pilot-unique-name.json"),
                          make_approved_client, Path("/absolute/path/to/zizmor"),
                          model=chosen_model, mode="live", approve_live_calls=True,
                          approve_source_disclosure=True)
```

Do not run this example with a real client before approval. Use a dedicated POSIX main-thread
application without an active alarm. The injected factory/SDK is trusted code and must provide
an in-memory transport for mock mode; the library cannot attest transport identity. Audit
results before sharing. Keep failures and actual source/code/model provenance, reconcile usage,
and report live and mocked measurements separately. A failed pilot stays private; an elapsed
week or passing mock suite does not authorize release. Any expanded experiment needs its own
scope/data/spend approval; existing cases must never be silently relabeled as new holdout data.
