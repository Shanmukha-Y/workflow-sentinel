# Review/repair contract investigation

The original local Qwen evaluation scored 4/8 and is unchanged in
[local-qwen38-first.json](../model_evaluation/results/local-qwen38-first.json). Both eligible
repairs and both abstention controls passed. The other four cases are examined here without
changing their expected labels or weakening deterministic safety checks.

## What the traces establish

Three manual-review cases requested evidence/proposal, received a repair refusal, then
abstained. The instruction-comment case requested validation after its proposal refusal;
the controller denied it without scanning/applying a patch. Responses were parseable; no
network, schema or budget failure accounts for these outcomes.

The original instructions said to abstain when evidence or validation was insufficient, but
did not distinguish unsupported repair from completed manual investigation. Tool descriptions
were generic and exposed validation even when its prerequisites were absent. The controller
already permitted finishing a manual review without a repair. The score correctly required
that useful completion; a conservative abstention was safe but incomplete, not an unsafe patch.
Classification and original scoring labels therefore remain unchanged.

The observed outcomes are consistent with an ambiguous contract. They do not prove the model's
internal cause, that a source comment caused the invalid validation request, or which part of
the combined fix produced improvement. There was no causal ablation or broad model comparison.

## General changes, no fixture-specific rules

Shared instructions/descriptions now distinguish evidence triage, repair eligibility and
validation. Verified `review` evidence plus repair `abstain` permits completing a manual review;
it does not permit claiming a fix, applying a patch or validating a nonexistent candidate.
Insufficient evidence, unsuccessful validation and genuine review uncertainty still abstain.

Tool observations include host-derived policy fields for review status, repair status and next
actions. These are derived from deterministic state, never source instructions or evaluation
labels. The native Ollama adapter advertises only actions whose prerequisites hold and constrains
packet indices to the corresponding eligible set. It checks returned calls against that set,
and the original controller independently checks order, candidate scope/hash, validation and
budgets. Abstention is always available. OpenAI retains its existing tool list but receives the
clarified shared descriptions/instructions and policy observations; its real-model behavior
remains untested. No category/case ID appears in production routing.

## Preserved evaluations

| Run | Policy completion | Requests | Wall time | Interpretation |
|---|---:|---:|---:|---|
| Original local baseline | 4/8 | 23 | 58.98 s | Original failures, unchanged |
| Contract development rerun | 8/8 | 23 | 111.86 s | Same eight cases, development regression |
| Fresh synthetic holdout | 6/6 | 17 | 74.88 s | First model execution of six exact fresh variants |

[Development record](../model_evaluation/results/local-qwen38-contract-development.json),
[first holdout record](../model_evaluation/results/local-qwen38-contract-holdout-first.json).
Both used the already downloaded Qwen3.8 27B/Q4_K_M digest and the same 8K/256-token/nonthinking/
temperature-0/seed-0 configuration. Production hashes and individual attempts/timings/usage are
retained. Runtime increased in these measurements; changing tool sets/prompt shape and host/
cache conditions were not isolated, so no performance improvement is claimed.

The development rerun completed the four previously failing reviews, retained both correct
abstentions and validated both supported repairs (four scanner calls). It checked 6/6 citations
and one required instruction payload exposure. The fresh suite contains non-Bash shell,
job permissions, privileged checkout, two exposed instruction-comment variants and a mismatched
snippet control. All six passed; 5/5 citation records, 2/2 payload exposures and original bytes
unchanged. The holdout contains manual reviews/abstention, not eligible repairs: no scanner
comparison or held-out repair-quality result is claimed for it.

Labels/source were committed before any fresh model execution (`463697f`). Manual source
review corrected a job-permission SARIF location before the run (`d4cf925`); its source and
expected label were unchanged. Self-authored, implementation-aware variants in known categories
are not independent/blind or a real-world vulnerability benchmark. The first fresh record must
never be overwritten, and later uses are regressions. No holdout result was used to retune code,
prompts, labels or generation configuration.

## Demo and release boundary

The consolidated demo generates review, preview, bounded agent/static validation and a summary:

```sh
python examples/review_demo.py --scanner /absolute/path/to/zizmor \
  --output-directory /tmp/sentinel-demo-unique
# Explicitly opt in to already-installed local Qwen inference:
python examples/review_demo.py --scanner /absolute/path/to/zizmor \
  --local-model qwen3.8:27b-q4_K_M --output-directory /tmp/sentinel-local-demo-unique
```

Output directories must be new before any inference/scanner work. The actual local demo
[summary](../model_evaluation/results/local-qwen38-contract-demo.json) records successful static
validation and unchanged source hashes. It uses one known synthetic fixture, not another holdout
or proof of security. The offline demo is exercised by CI; CI/unit tests make no local/live
inference calls.

The four original failures are resolved on this measured scope, with a first-use synthetic
check of affected categories. Model limitations remain: one model/host/configuration, known
categories, tightly guided action selection, no independent detection, no broad adversarial
resistance/effectiveness or multi-finding evaluation, no real OpenAI model validation. Static
checks do not prove security. Permission repair and checkout changes remain unsupported/report-only.
The repository remains private pending human release authorization and honest acceptance of
these limits. No paid/cloud calls, credential configuration, deployment or social release occurred.
