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
A bounded advisory interpreter and offline scripted adapter demo are implemented. Live provider
integration and model evaluation remain open gates; replay does not establish model quality.
Next: release preparation with a reproducible demo, threat model and measured limitations;
retain private visibility until separate release authorization.
