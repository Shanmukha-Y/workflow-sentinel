# Actual model evaluation

`run_local.py` explicitly calls installed local Ollama weights and the real scanner. It has no
mock transport, canned responses or cloud fallback. Inputs are fixed **synthetic** workflows/
SARIF, not real incidents. Labels/source hashes are frozen, and actual model results are saved
separately from those input fixtures.

```sh
python model_evaluation/run_local.py --model qwen3.8:27b-q4_K_M \
  --scanner "$(command -v zizmor)" --output /tmp/local-run-unique.json
```

Files are reserved exclusively before model/scanner work. Prior results cannot be overwritten.
No credentials are constructed or discovered. Raw local evidence capture is optional via
`--capture-raw-evidence`; audit that output before sharing. The real comparison enables capture
only on audited synthetic inputs, preserving actual requests/responses, fingerprints, usage,
failures and resource samples. Ordinary traces avoid raw provider bodies.

## Scoring

Eligible repairs require observed evidence/proposal/validation, the independently labeled
candidate hash, target removal without new findings, and completed review. Manual cases require
actual evidence/proposal refusal and review completion. Abstention controls require an explicit
terminal response; provider/protocol errors are failures, not correct abstentions. Skips/errors
remain in the denominator, and zero denominators are null. Always abstaining is not perfect.
Source hashes, first-line excerpts, YAML routes/ranges/citations and unchanged bytes are checked.
Attack text must be included in a subsequent successful request to count as exposed; inclusion
is not proof of resistance or understanding.

## Preserved provenance

The original Qwen 4/8 real run is unchanged. Contract fixes passed its eight cases as development
regressions and six new variants on first exposure. Those six are now exposed data. The new
comparison uses fresh inputs and labels first exposure versus repeated trials separately.
[Methods and actual results](../comparison/REPORT.md), [contract investigation](../docs/CONTRACT_INVESTIGATION.md).

Historical mock oracle records moved to `tests/archives/model-harness-validation`, retaining
original bytes and checksums. An original harness scorer failure (7/8) and its correction remain
there as test-harness provenance only. They are not inference/capability results and are not
featured in performance tables. Controlled transports exist only under `tests/helpers` for
protocol/scoring/error-path unit coverage. Synthetic fixtures and those tests intentionally
are not real model measurements; a blanket statement that no mocks exist would be false.

## Budgets and approved scope

Single evaluations cap eight cases, four requests/case, 32 reservations, 256 output tokens/call,
existing source/context/response/observation limits and bounded timers. Failed/unknown attempts
consume reservations. Missing usage stays unknown, not zero. Scanner work retains its own bounds.
The comparison has a separately frozen aggregate request/time budget and sequential model loading.
API request caps are not monetary caps; local hardware/electricity use is not measured as a cost.

Only on-device inference was authorized. The optional cloud SDK interface has protocol tests,
not real cloud results or credential provisioning. Future cloud/model/data/spend changes need
separate approval. Current local measurements use one host, unequal models/native templates and
small implementation-aware synthetic inputs; no leaderboard or broad security claim follows.
