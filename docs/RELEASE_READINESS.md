# Release readiness — private development

Workflow Sentinel remains private. Passing tests and reaching the end of the original week do
not establish live capability or authorize a release.

| Gate | Current evidence | Remaining requirement |
|---|---|---|
| Bounded investigation/repair/static validation | Unit suite and 38-case deterministic regression; isolated scanner comparisons | Preserve narrow scope and documented refusals |
| Provider integration | Official SDK in-memory transport tests and offline scanner demos | OpenAI unverified; local baseline 4/8, development 8/8, fresh synthetic 6/6 |
| Model evaluation tooling | Fixed eight-case known synthetic suite, scoring tests, request caps and preserved scorer failure | Original failures retained; general contract fix tested without relabeling |
| Threat model | THREAT_MODEL.md documents assets, trust assumptions and known limits | Review alongside actual live behavior and disclosure/spend plan |
| Private data/secrets | October 13 repository audit below | Re-audit the final release tree/artifacts; review any live results |
| Reproducible release and public visibility | Consolidated offline/local demo verified; measured limits documented | Human release authorization and manual release decision/draft |

A proposed OpenAI/cloud pilot would use exactly eight known synthetic cases, at most four provider
attempts per case/32 overall, and at most 256 requested output tokens per call/8,192 overall.
Unknown/failed attempts consume reservations; errors/skips stay in the eight-case denominator.
Provider errors cannot be relabeled correct abstentions. The harness checks attack-text payload
inclusion, not whether a model resisted the text. Details and user-run instructions are in
[model_evaluation/README.md](../model_evaluation/README.md).

Local model download/inference was separately authorized and the real Qwen run is preserved in
LOCAL_MODEL.md. No paid cloud call or monetary commitment is authorized. A reliable dollar estimate/limit needs a
selected supported model, current input/output pricing, disclosure approval, usage reconciliation
and an explicitly approved enforcement method. Token, byte and request caps alone do not enforce
cash spend. On-device inference incurred no API charges; hardware/electricity costs were not measured.

## October 13 repository audit

Inspected 62 current tracked/new project files and 93 reachable historical Git blobs with
credential patterns (GitHub tokens, AWS access-key IDs, private-key headers and OpenAI-style
keys), sensitive filenames and private home-path detection. No matches requiring removal were
found. Synthetic workflows/SARIF, example reports and new evaluation archives were reviewed for
scope: data is synthetic; records omit raw provider bodies, prompts, credentials and source
excerpts. Fixed mock authentication placeholders are intentionally non-credentials.

Scope excludes ignored environments/caches and files outside this repository. Pattern/filename
and content review is not proof that every secret or private datum is absent, nor dependency
vulnerability or supply-chain verification. No personal credential stores were searched.
A final audit must include any future live results before public sharing.

## Actual local quality gate

The first Qwen3.8 27B local run completed all eight cases in 58.98 seconds using 23 model requests.
Both supported repairs and both abstention controls passed. Three manual-review cases abstained
instead of completing review; the source-instruction case requested validation after a refused
proposal and the deterministic guard blocked it. Score: 4/8. This genuine but narrow capability
measurement is retained separately from mocks, with its failures. The repository stays private;
Contract remediation subsequently passed 8/8 development and 6/6 fresh synthetic cases; the
consolidated demo passed. Human release authorization and acceptance of narrow scope/model
limitations remain. See CONTRACT_INVESTIGATION.md.
