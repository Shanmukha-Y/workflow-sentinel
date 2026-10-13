# Advisory adapter contract

`workflow_sentinel.agent.run(sarif, repo, responses, scanner=None)` implements the offline
request interpreter. The bundled scripted transport and opt-in injected OpenAI adapter are supported. It creates
the same bounded deterministic packets first, then interprets a sequence of structured
requests. The default replay loads no provider SDK. The provider path accepts only a trusted injected
client; it loads no source-defined tools, plugins or shell strings.

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

## OpenAI transport implementation and remaining gate

`OpenAIAdapter(client, model=..., max_output_tokens=..., allow_source_disclosure=True)` is an
opt-in interactive transport. It calls the supplied synchronous SDK client's
`with_options(timeout=..., max_retries=0).responses.create(...)`. The request uses five strict
function schemas, `tool_choice="required"`, `parallel_tool_calls=False`, `store=False`, and an
explicit output-token cap. It accepts exactly one completed function call, validates the
arguments again locally, rejects duplicate call IDs/JSON keys and returns the command to the
same deterministic interpreter. Bounded reasoning items are preserved for continuation, and
the next call receives the actual preceding observation using `function_call_output/call_id`.
Raw provider response/errors are not included in report traces.

Verified on October 12 against the [official function-calling guide](https://developers.openai.com/api/docs/guides/function-calling)
and [official SDK guidance](https://developers.openai.com/api/docs/libraries). Tested SDK:
OpenAI Python 3.29.0 with httpx2 2.13.1 in-memory MockTransport. No live requests or real
credentials were used. The SDK tests verify the emitted request payload, multi-turn observation
roundtrip, reasoning continuation, retries disabled on HTTP 429, strict configuration, malformed/
refused/incomplete output, arbitrary commands/patches, duplicate call IDs/arguments, input and
output caps, deadline restoration, and missing scanner refusal. A standalone mock transport
demo can also use the real installed scanner on the synthetic repair fixture.

The transport permits only `https://api.openai.com/v1`. A caller must separately approve data
and spend, supply the client and supported model, and review excerpts for secrets. The adapter
never discovers credentials or constructs clients. The test/demo uses a fixed mock placeholder
and clears the SDK's environment during mock client construction; no real credential is read.
There is no live CLI option. SDK dependencies are optional for runtime users.

Resource bounds: eight requests, 64 KB serialized conversation history, 16 KB decoded provider
response, 4 KB function arguments, 64–512 output tokens/request. The existing 64 KB observation
and two scanner-pair caps remain. Each call uses a POSIX main-thread signal wall deadline of at
most 15 seconds, capped by the session's remaining 65-second budget, plus SDK timeout. Active
process alarms and non-main threads are refused; use a dedicated single-thread application and
a fresh unused client. Trusted SDK/native code could delay signal delivery; this is not process
isolation. Output size is checked after SDK decoding, not a preallocation/streaming cap.
Cancelling a local request does not establish remote cancellation or zero charges. Token/byte
caps do not enforce a monetary budget, and `store=False` is not a provider retention guarantee.

OpenAI implementation is present but its real cloud capability is unvalidated. The separate
local Ollama adapter has an actual 4/8 Qwen result; see LOCAL_MODEL.md. Release needs
separately approved real-model evaluation with malicious source instructions, measured failure/
refusal behavior, explicit cost/data limits and available model/account compatibility. SDK mocks
establish protocol and guard behavior only. Existing frozen cases are regressions; do not relabel
them as new held-out model cases. The documentation must not call replay or mocked transport
autonomous LLM reasoning or claim static validation proves security.
