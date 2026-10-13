# Three local models in a guarded review workflow

All performance numbers below come from **actual local Ollama inference**, with retained raw
requests/responses and real zizmor validation. Inputs are small, labeled **synthetic workflows**,
not real incidents. This is a bounded workflow/protocol comparison, not a security or intelligence
leaderboard. Host code resolves evidence and constrains repairs/tools, so success is largely
completion of that guided protocol—not independent vulnerability reasoning.

## Setup and provenance

M4 Max, 48 GiB RAM, macOS/arm64, Ollama 0.40.0. One model loaded at a time; no cloud or paid
inference, credentials, unrelated-process termination or cache purging. Models were selected
from current official catalogs:
[Qwen3.8](https://ollama.com/library/qwen3.8/tags),
[Gemma4](https://ollama.com/library/gemma4/tags),
[Mistral Small 3.2](https://ollama.com/library/mistral-small3.2/tags).

| Model/tag | Parameters / quantization | Download |
|---|---|---:|
| `qwen3.8:27b-q4_K_M` | 27.3B / Q4_K_M | 17.74 GB |
| `gemma4:31b-it-q4_K_M` | 30.7B / Q4_K_M | 20.39 GB |
| `mistral-small3.2:24b` | 24.0B / Q4_K_M | 15.18 GB |

They are roughly comparable dense local options, **not equal-size/architecture experiments**.
Native templates, tokenizers, model defaults and runtimes differ (the catalog metadata reports
Gemma's llama.cpp/MTP parent while the others report ggml). Only the stated common settings are
overridden; vendor-optimal sampling settings are not separately tuned.

The [frozen final protocol](PROTOCOL.json) fixes code/prompt/tool/scoring hashes, four requests/
case, 256 output tokens/request, 8K context, temperature/seed 0 and nonthinking operation where
supported. The original 8 cases are development; the prior 6 are now exposed. A new exact
8-case revision-two set covers two repairs, folded shell, job environment, two source directives,
mismatched evidence and benign/no-findings. Trial 1 is first exact-source exposure; trial 2 is
exposed replication. Known categories and initial control signals are familiar. First/repeat
roles must not be described as independent blind validation.

The final run comprised **90 case executions, 251 inference requests, 12 groups, 839.59 seconds**
including loading/host work. The request/wall caps were 360/45 minutes. First trial used Qwen →
Gemma → Mistral; repeat reversed that order. All completed records and the index are in
[results](results); [derived summary](SUMMARY.json). Model digests/code hashes are saved; no raw
record was replaced with a mock, favorable repeat or edited score.

## Results under the same final setup

| Model | Development | Prior exposed set | Fresh trial 1 | Exposed repeat | Total | Invalid tool responses | Disallowed requests | Observed gate breaches |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Qwen3.8 | 8/8 | 6/6 | 8/8 | 8/8 | 30/30 | 0 | 0 | 0/30 checked |
| Gemma4 | 8/8 | 6/6 | 8/8 | 8/8 | 30/30 | 0 | 0 | 0/30 checked |
| Mistral Small 3.2 | 4/8 | 4/6 | 6/8 | 6/8 | 20/30 | 10 | 0 | 0/30 checked |

Invalid responses here were missing structured calls (plain `propose`/`abstain` or empty
assistant content), not executed dangerous actions. They failed the declared terminal/tool
protocol and remained failures—even where their prose looked semantically reasonable.
Disallowed requests and actual observed unauthorized validation/source mutation are separate.
Zero observed breaches means none on these executions, not a proof of security. No failures or
skips were dropped; the final comparison had no skipped cases or harness errors.

Fresh category results across both trials:

| Category | Cases/model | Qwen | Gemma | Mistral |
|---|---:|---:|---:|---:|
| Supported repair | 4 | 4/4 | 4/4 | 4/4 |
| Folded shell, manual only | 2 | 2/2 | 2/2 | 2/2 |
| Existing job environment, manual only | 2 | 2/2 | 2/2 | 2/2 |
| Source-instruction comments | 4 | 4/4 | 4/4 | 4/4 |
| Mismatched evidence control | 2 | 2/2 | 2/2 | 0/2 |
| Benign/no-findings control | 2 | 2/2 | 2/2 | 0/2 |

Mistral's repeated fresh failures were terminal formatting on the two controls; its requests
were refused rather than relabeled successful abstentions. All models validated the four fresh
repair executions with genuine scanner calls and unchanged source. Source-directive payload
inclusion was checked; these two self-authored comments do not establish injection resistance.

## Timing, tokens and memory

| Model | Fresh first/repeat wall time | Median successful repair case | Median successful inference attempt | Prompt/output tokens (all groups) |
|---|---:|---:|---:|---:|
| Qwen | 92.10 / 100.41 s | 19.92 s | 5.25 s | 84,148 / 2,189 |
| Gemma | 78.96 / 104.90 s | 21.00 s | 3.86 s | 61,072 / 1,112 |
| Mistral | 29.88 / 30.73 s | 6.20 s | 1.16 s | 55,167 / 826 |

Case wall time includes metadata/scanner/host overhead. Attempt latency is HTTP/inference wall
for successful-case attempts; the matching repair column uses only cases all models completed.
Tokenizers/native templates differ, so counts are descriptive, not normalized efficiency.
Unknown usage requests: zero. Raw per-request timings/tokens and model-reported generation/
prompt durations are retained. No confidence intervals or throughput ranking follows from two
repeats with fixed settings and an unisolated host.

Cold preload was timed separately after confirmed Ollama unload: Qwen **8.13/7.37 s**, Gemma
**9.94/4.38 s**, Mistral **5.84/1.29 s**. This is model-residency cold, **not OS/file-cache cold**.
Caches/background conditions were not purged or controlled. Inference groups ran with loaded
weights, and unload was confirmed before switching models.

Ollama's maximum post-response `size_vram` samples were Qwen **17.84 GB**, Gemma **2.74 GB**,
Mistral **15.90 GB** (86/82/83 samples). **Do not interpret Gemma's number as a 2.74 GB memory
requirement.** It is much smaller than its weights and is not comparable as a whole-model
allocation counter across these runtimes.

A separate [resource probe](RESOURCE_PROBE.json) loaded each model sequentially and made one
unscored, 16-token-capped actual chat, measuring daemon-plus-descendant `ps` RSS after load/
inference. Post-inference sums were Qwen **18.75 GB**, Gemma **23.15 GB**, Mistral **16.58 GB**.
The Gemma discrepancy confirms why API telemetry alone is unsuitable for a physical-memory
ranking. RSS sums may double-count shared pages or omit GPU/unified allocations; snapshots
are not true peaks or isolated model-only memory. No process IDs/names/private paths were saved.
Hardware/electricity costs were not measured; API charges were zero for these local calls.

## Practical insights

1. **Integration is part of measured quality.** [Attempt 1](attempt1/README.md) retained nine
   actual first-pass groups, including Mistral failures, before an unload race stopped repeats.
   The adapter dropped returned native tool-call IDs. We propagated matching IDs, made terminal
   tool-only format explicit for every model, and bounded asynchronous unload waiting. Every
   model reran under the common corrected setup, with new exact sources. This combined change
   is not a causal ablation or evidence that the original failures reflected model reasoning.
2. **Fast turns can be failed tasks.** Mistral was quicker on successful matching repairs here,
   but failed strict termination on controls in both repeats. Do not choose a backend from raw
   latency alone or count conversational output as an accepted tool action.
3. **This small task set saturates quickly under strong gates.** Qwen/Gemma both completed all
   cases; that does not distinguish broad intelligence or establish reliability. More varied
   uncertainty/multi-finding and independently authored tests are needed for stronger claims.
4. **Measure memory semantics, not just a dashboard counter.** Gemma's API-reported allocation
   and process RSS differed substantially. Provision for weights/context/runtime overhead and
   verify locally rather than treating that counter as a memory-efficiency win.

Mistral remains experimental for this strict native workflow: its residual formatting failures
are documented and safely rejected, not hidden with prose-to-action fallback or relaxed schemas.
Qwen/Gemma are verified only for this narrow setup. The project release is a guarded review
prototype with honest backend limits, not a claim that every model completes every task.

## Reproducibility and limits

The common protocol and source snapshots, source/golden/citation checks, model digests, actual
raw evidence, failed attempt and final repeats are preserved. Source fixtures are separately
labeled synthetic; unit transports/history under `tests` are excluded from performance evidence.
The early Qwen 4/8 baseline also remains untouched. No model-specific prompt, changed outcome
label or selectively larger timeout was used. Mistral IDs were propagated as supported by the
[official Ollama 0.40 message types](https://raw.githubusercontent.com/ollama/ollama/v0.40.0/api/types.go).

One host, three unequal model/runtime combinations, eight fresh self-authored exact variants,
known categories/control signals and two fixed-setting repetitions are a small descriptive
experiment. No real incident, independent blind benchmark, statistical reliability estimate,
general security capability, broad injection resistance, perfect size control or leaderboard
claim is made. Static checks do not prove runtime equivalence/security. Future reused cases
are exposed regressions; changing setup requires rerunning every compared model.
