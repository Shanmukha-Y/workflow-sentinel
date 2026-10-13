# Bounded local model comparison

This directory contains actual Ollama inference measurements, not prerecorded model responses.
Input workflows/SARIF are explicitly synthetic, not real incidents. Model weights, official
catalog selection, a common protocol and raw evidence are recorded. No cloud/paid inference,
credential provisioning or simultaneous model loading is used.

The selected dense models have unequal sizes and native templates: Qwen3.8 27.3B/Q4_K_M,
Gemma4 30.7B/Q4_K_M and Mistral Small 3.2 24.0B/Q4_K_M. They are reasonably comparable local
options, not a controlled parameter-size or architecture experiment. Their native runtimes and
model defaults can affect latency/behavior even with common overridden generation settings.

## Roles and repetitions

The original eight cases are development data. The previous six-case synthetic holdout is now
exposed data. A first fresh comparison set was frozen before attempt 1; its real records are
retained even though that attempt stopped before repeat trials. An integration correction
required all models to rerun, and a second exact fresh set was frozen before that final setup.
Its first trial is first exact source exposure; its second trial is exposed replication. Known
categories/control signals are familiar, not independent blind information. Two repetitions
with fixed settings are descriptive repeatability checks, not statistical reliability estimates.

## Correction provenance

Attempt 1 retained successful Qwen/Gemma runs and failed Mistral runs. The adapter dropped native
tool-call IDs, and the common instruction did not explicitly forbid replacing terminal tool
calls with prose. Mistral emitted prose/malformed requests; those were failures, not accepted
reviews. An immediate unload-confirmation check raced asynchronous unloading and stopped the
run before repetitions. Original raw outputs, source snapshots and protocol remain under
`attempt1`; they were not edited into successes.

The general correction preserves returned IDs and sends matching `tool_call_id` on tool outputs,
clarifies one-tool-call/zero-argument abstention for every model, and waits boundedly for unload.
[Ollama 0.40 API message types](https://raw.githubusercontent.com/ollama/ollama/v0.40.0/api/types.go)
include the ID fields. All models run under the same revised setup; no model-specific prompt,
looser schema, changed label or selectively increased budget is used. This bundle is not a
causal ablation: ID handling versus instruction changes are not isolated.

## Reproduce

Install the project and trusted native zizmor 1.30.1. Pull the three official local tags separately,
then verify Ollama listens only on loopback and no other model job is active. Downloads are not
automatic in the runner. Frozen production files must match PROTOCOL.json before inference.

```sh
OLLAMA_HOST=127.0.0.1:11434 ollama pull qwen3.8:27b-q4_K_M
OLLAMA_HOST=127.0.0.1:11434 ollama pull gemma4:31b-it-q4_K_M
OLLAMA_HOST=127.0.0.1:11434 ollama pull mistral-small3.2:24b
python comparison/run.py --scanner "$(command -v zizmor)" \
  --output-directory /tmp/sentinel-comparison-unique
python comparison/summarize.py /tmp/sentinel-comparison-unique \
  --output /tmp/sentinel-comparison-summary-unique.json
```

All reruns of already-published fixtures are exposed regressions. Fresh output directories/files
are required. Completed per-group records survive an interrupted run; failures/skips remain in
denominators. The final runner caps 360 inference attempts and 45 minutes, four attempts/case,
32/group, 15 seconds/inference request and 256 requested output tokens, with existing source/
byte/context/scanner limits. Dataset role, frozen source hashes and model digests are recorded.

Cold empty-prompt preload is measured separately after confirming no model residency; "cold"
means Ollama-unloaded, not deliberately purged OS/file cache. Actual inference then uses the
loaded model. Trial 2 reverses model order. Unload is confirmed before another model loads.
Memory is the maximum **sampled** Ollama `size_vram` after responses, not process RSS, whole-host
memory or a true GPU/host peak. Wall time includes host/scanner/metadata overhead; model-reported
prompt/generation durations and token counts are retained. Tokenizers/templates differ, so raw
token counts are not normalized model-efficiency measures. No unrelated applications/cache are
stopped or purged, and host/background conditions are not controlled.

Raw requests/responses may contain synthetic source excerpts and model prose. They are retained
only for audited input fixtures and checked before publication. No raw model output is used as
a future response. Test-only mocks live under `tests` and are excluded from performance tables.
[Actual results and scoped insights](REPORT.md) disclose every final trial and earlier failure.
