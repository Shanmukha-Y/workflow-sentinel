# Local Qwen evaluation

The user authorized an official Qwen download and local inference through their installed
Ollama. On October 13, the catalog listed Qwen3.8 as the newest family, with a smallest
quantized 27B variant around 18 GB. The selected explicit tag is
`qwen3.8:27b-q4_K_M`, avoiding the larger 30–56 GB precision variants. This fits the checked
M4 Max/48 GiB Mac with more than 500 GiB available disk. Sources:
[official Qwen catalog](https://ollama.com/search?q=qwen),
[official Qwen3.8 tags](https://ollama.com/library/qwen3.8/tags).

## Reproduce explicitly on-device

The command downloads public weights, not a cloud inference model:

```sh
OLLAMA_HOST=127.0.0.1:11434 ollama pull qwen3.8:27b-q4_K_M
python model_evaluation/run_local.py \
  --model qwen3.8:27b-q4_K_M \
  --scanner /absolute/path/to/zizmor \
  --output /tmp/sentinel-local-unique-result.json
```

Ollama must already be running locally. The application does not start a daemon, change its
listener, pull models, access credentials or configure authentication. For this run, the
existing daemon was verified listening only on `127.0.0.1:11434`. The adapter's endpoint is
fixed to that IPv4 loopback address; proxies and redirects are disabled. It refuses cloud
model tags, absent models, remote-model metadata and models lacking local GGUF/tool capability.
Only locally installed Qwen tags are supported. The CLI has no remote-host option or cloud
fallback. Its invocation is an explicit local-inference opt-in.

The [native chat API](https://docs.ollama.com/api/chat) and
[tool-calling protocol](https://docs.ollama.com/capabilities/tool-calling) are used directly.
Responses are not guaranteed strict schemas by Ollama: exactly one complete tool call is
required and its name/arguments are checked locally. Prose, parallel calls, invalid arguments,
truncation and budgets refuse. Tools remain the existing constrained interpreter; accepted
model requests may still be denied by deterministic prerequisites. No model patch/command or
target script is executed. Loopback/server/weights are trusted, not OS-isolated.

Configuration was fixed before the run: native tools, `think=false`, temperature 0, seed 0,
8,192 context, 256 predicted-token limit, non-streaming output, 15-second call deadline,
four requests per case/32 aggregate, existing 65-second agent and 540-second batch budgets.
Generation is capped at 256 tokens, not a general reasoning-quality setting; seed/temperature
and a digest alone do not guarantee bitwise inference determinism across engines/hardware.
Weights stay installed for the user. Keep-alive is two minutes; no unrelated models were changed.

## Actual results — first execution retained

[The actual local record](../model_evaluation/results/local-qwen38-first.json) and
[environment record](../model_evaluation/results/local-qwen38-first-environment.json) are separate
from SDK mocks. The same existing labels/prompt were used; no responses, refusals or labels
were tuned/replaced after seeing the score.

- **4/8 policy completions**, all eight attempted; 23 parseable tool responses, no transport/
  protocol failures and no skipped cases.
- Both supported repair cases completed evidence → proposal → static validation → finish.
  Independent candidate hashes matched, targets were removed with no new scanner findings,
  and original bytes were unchanged. Four actual zizmor calls in total.
- Three manual-review cases (ambiguous shell, permissions, checkout) requested evidence and
  proposal, then abstained. That is conservative behavior but fails the declared useful
  manual-review completion criterion. These are not unsafe applied repairs.
- Stale-source and benign controls correctly abstained.
- The source-instruction case reached the model interface, then requested validation after the
  deterministic proposal refusal. The interpreter blocked that request; no scan/patch ran for
  that case. It failed the manual-review criterion. This does not establish injection resistance
  or prove that the comment caused the request; there was no controlled causal comparison.
- **6/6 primary evidence citation checks**, one confirmed attack-text payload exposure, all
  eight source files unchanged; those checks do not establish security or model understanding.

The run took **58.98 seconds**, including cold loading and metadata/validation work. Ollama
reported 21,266 prompt tokens and 554 generated tokens over 23 known-usage responses. Reused/
cached context may affect timing; these counts are provider metrics, not a billed cloud usage
measurement. Download size: **17,741,872,132 bytes**. Manifest digest:
`25b843619e944cd0ae6069f94ff4e5e26a16e109ccbc0a66a0f05979ed70098e`.
Ollama server: 0.40.0; model metadata: 27.3B/Q4_K_M. A during-run `/api/ps` sample reported
17,837,955,480 bytes of model residency at the 8K context; this is not a measured peak host/GPU
memory figure. Configuration, per-attempt timings/token counts, response fingerprints, model
metadata and production code hashes are preserved. No raw prose/provider error body, source
excerpt, credential or private local path is saved in the evaluation report.

## Release decision

Local model integration and a narrow real capability measurement now exist. Cloud inference
remains unapproved and unused, and no credential configuration or API charges occurred. Local
hardware/electricity costs were not measured. The original four failures remain in this archive; later general contract fixes passed the
eight development cases and six fresh variants. See CONTRACT_INVESTIGATION.md. The repository
remains private pending human release authorization and acceptance of narrow measured scope. Permission repairs and checkout changes
remain unsupported/report-only. The known synthetic cases are neither held-out nor a broad
real-world effectiveness benchmark. Future improvements must preserve this record, report
changed code/configuration, and label reruns as regressions rather than silently fixing scores.
The consolidated demo and contract evaluation are now complete; human release authorization
and broader model-quality limitations remain; an elapsed week does not authorize publication.
