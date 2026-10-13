# Seven-day roadmap

| Day | Deliverable | Acceptance gate |
|---|---|---|
| 1 | Offline CLI, schemas, synthetic fixtures, tests and CI | Deterministic packets, bounded reads, abstention; no target execution |
| 2 | Evidence investigation | YAML-aware context, revision provenance, permissions and trust boundaries; bounded read-only tools |
| 3 | Constrained repairs | Allowlisted injection/permission patches; ambiguous cases abstain; untrusted checkout report-only |
| 4 | Validation loop | Parse/diff checks, offline zizmor rerun, capped iterations; static checks do not prove security |
| 5 | Adversarial/held-out evaluation | Frozen dataset; precision, recall, abstention and repair validity; record failures |
| 6 | Optional model integration | Opt-in adapter, schema validation, prompt-injection tests, cost/privacy gates; offline baseline |
| 7 | Release | Reproducible demo, threat model, measured results and limits; human review and manual release draft |

One increment per day. Update progress with actual checks and blockers. No automatic schedule
or social posting configured. Public visibility requires a separate release action.

Current status: evidence investigation and a constrained Bash `printf` injection repair preview
are implemented. Permission repairs remain deferred until explicit requirements can be supplied
and validated. The bounded static validation loop is implemented for eligible repair previews.
A frozen synthetic evaluation and first-run audit are complete; later runs are regressions.
A bounded advisory interpreter, offline scripted demo and opt-in OpenAI Responses provider
adapter are implemented. SDK mock transport tests pass; live-model evaluation remains an open
release gate, and neither replay nor mocks establish model quality.
An eight-case synthetic model evaluation harness and threat model are now available. The
mock oracle verifies scoring/budgets; no live-model result or monetary approval exists.
Next: obtain separate user approval for the bounded live pilot's model, data disclosure and
substantiated spending ceiling, then measure capability/failures. Retain private visibility;
consolidated demo and human release decision remain open gates.
