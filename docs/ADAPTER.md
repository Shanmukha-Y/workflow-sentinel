# Advisory adapter contract

`workflow_sentinel.agent.run(sarif, repo, responses, scanner=None)` implements the offline
request interpreter. Only the bundled data-only scripted transport is supported. It creates
the same bounded deterministic packets first, then interprets a sequence of structured
requests. No callable plugins, provider SDKs, shell strings or source-defined tools are loaded.

| Request | Prerequisite | Observation / outcome |
|---|---|---|
| evidence | Valid packet index | Verified source evidence and deterministic triage |
| propose | Evidence previously requested | Existing allowlisted repair preview or refusal |
| validate | Proposed candidate, explicit scanner, unused packet, remaining budget | Existing static validator result |
| finish | Prior evidence; any proposal successfully validated | Advisory review or deterministic abstention |
| abstain | None | Terminal abstention |

Terminal responses must be last. Exhaustion, invalid structure/order, deadline, missing scanner,
failed validation and oversized observations abstain. Requested source evidence is data, never
instructions. Response text is not stored in sanitized traces. Output source excerpts and diffs
are not redacted: keep reports private and review before sharing. The interpreter does not
accept a model's security verdict or supplied patch, even if its narrative appears plausible.
A review outcome is not authorization to apply a patch and does not prove security.

The script can be reproduced with the README command. Unit tests cover malformed and malicious
requests, boolean/negative/out-of-range indices, arbitrary commands/paths/patches, bad evidence,
sequence ordering, repeated validation, response/observation/turn/deadline bounds, unavailable
scanner opt-in, rejected/unsupported/unavailable results, trace sanitization, deterministic
replay and unchanged source. Real scanner CI exercises one scripted successful proposal;
that is a scanner integration demonstration, not a model evaluation.

## Live transport feasibility and release gate

The interpreter is a narrow seam for a future provider, but replay is not an interactive LLM
agent. A live transport must receive the previous bounded observations and supply one response
at a time, with strict JSON decoding (including duplicate-key rejection), cancellation and a
hard network deadline enforced outside the interpreter. It must not change available tools,
turn/scanner budgets, source-read bounds, or the deterministic proposal/validation policy.

Before adding one, verify current official provider API/SDK documentation, select a supported
structured-output mechanism, bound requests and responses, disable automatic retries, and
handle refusal, malformed responses, transport errors and cancellation without recording raw
provider bodies. Require explicit provider, model, data-disclosure and spend configuration.
Credentials must come from a user-approved runtime mechanism; never discover credentials by
searching files, store them in reports, or include them in prompts. No provider is selected,
no credential is read, and no network model request is made by this implementation.

Release evidence still needs a separately approved live-model evaluation, including malicious
source instructions and refusal/timeout handling, with measured failures and explicit cost/data
limits. Existing frozen cases are regressions now; do not relabel them as new held-out model
cases. Mocked responses establish interpreter behavior only. Adding a provider requires a new
implementation and review; setting an environment variable cannot enable one today.
