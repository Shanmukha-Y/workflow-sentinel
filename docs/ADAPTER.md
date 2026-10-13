# Bounded model adapter contract

The product `workflow_sentinel.agent.run(sarif, repo, scanner, adapter=...)` requires an actual
configured adapter. It first resolves bounded deterministic packets, then interprets each model
request. There is no scripted-product CLI or canned response fallback. The private execution
seam is used only by controlled unit tests.

| Request | Prerequisite | Outcome |
|---|---|---|
| evidence | Valid eligible packet index | Verified local source evidence and triage |
| propose | Evidence already reviewed | Deterministic constrained preview or manual-only refusal |
| validate | Proposed candidate, scanner opt-in, unused validation budget | Existing static validator |
| finish | Verified manual review or successfully validated proposal | Advisory completion, no application |
| abstain | Always | Terminal abstention |

Host-derived policy fields distinguish review status from automatic-repair status. Unsupported
repair with verified review evidence can complete manual review; it does not claim a fix.
Insufficient evidence and unsuccessful validation abstain. Native tool advertising restricts
actions and packet enums by those prerequisites; returned requests and the controller check
again independently. Source excerpts/comments cannot change host state or available tools.

Sessions have eight-turn/response/observation/deadline caps and at most two validation pairs.
The comparison harness tightens to four requests/case and an aggregate budget. Scope/hash/YAML
and before/after scanner checks are deterministic; model-provided paths, commands, arbitrary
patches and security verdicts are not accepted. No target workflow/script or model shell command
is executed. Reports contain source excerpts; default provider traces avoid raw bodies.

## Native local Ollama

`OllamaAdapter` uses the [native chat/tool protocol](https://docs.ollama.com/capabilities/tool-calling)
on a fixed proxy-free, redirect-free `http://127.0.0.1:11434`. The daemon must already exist.
Installed local GGUF/tool-capable Qwen, Gemma and Mistral Small tags are supported; cloud tags/
remote metadata refuse. No server/credential configuration or automatic download occurs.
Native outputs are not assumed strict: one complete call, correct field types/index/action and
satisfied prerequisites are required. Prose, parallel calls, truncation and invalid requests
refuse without running tools. Native timings and usage are recorded when supplied.

Calls use an 8K context, 256-token cap, temperature/seed 0, and thinking disabled where supported
(the nonthinking model has no think field). A 15-second POSIX main-thread wall deadline and
socket timeout cap each call; active process alarms or non-main threads refuse. Trusted native
code can delay signal delivery; this is not OS isolation. Source/observation and response byte
limits still apply. Default traces are minimized; opt-in comparison capture retains bounded
actual raw requests/responses only for the explicitly audited synthetic datasets. Those records
must be audited before sharing and are not appropriate for unaudited private source content.

## Optional OpenAI transport

`OpenAIAdapter` accepts a caller-supplied fresh synchronous SDK client, explicit model/token cap
and source-disclosure opt-in. It uses strict function tools, `tool_choice="required"`, no parallel
calls, `store=False`, retries=0 and timeout. It validates output locally and returns each bounded
observation through the Responses continuation protocol. No credential discovery/client
construction is implemented. No real cloud-model evaluation has been performed; test transports
establish protocol/error handling only. Local results do not establish this adapter's quality.

Verified implementation references: [official function calling](https://developers.openai.com/api/docs/guides/function-calling),
[official SDK guidance](https://developers.openai.com/api/docs/libraries). Tests use SDK 3.29.0
and httpx2 2.13.1 controlled transports under `tests`; they are not product-performance results.

OpenAI history/decoded-response/argument/token bounds apply. Input/output limits are checked
around SDK processing, not an allocation-proof streaming cap. Local cancellation does not
establish remote cancellation or zero charges, and store=False is not a retention guarantee.
Any cloud use still needs explicit data/spend approval. Request caps are not monetary caps.

## Evidence and limitations

Actual local baselines, development reruns, exposed data and fresh/repeated comparison trials
are separated in [the comparison report](../comparison/REPORT.md). The unchanged original
failure and the general contract fix are documented in CONTRACT_INVESTIGATION.md. Historical
mock/model-oracle records are test-only provenance under `tests/archives`, never model-quality
evidence. Source cases are synthetic, not real incidents. Guided tools and a small self-authored
set do not prove broad reliability, injection resistance, vulnerability detection or security.
