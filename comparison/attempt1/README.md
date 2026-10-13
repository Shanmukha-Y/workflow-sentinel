# Actual interrupted comparison attempt 1

These are genuine local inference records, not mock/test-harness data. Nine trial-one groups
completed; no second-trial groups ran. The runner stopped on an immediate unload-confirmation
race. A later loopback /api/ps probe confirmed no model remained loaded.

Qwen/Gemma completed their tasks. Mistral emitted prose or extra arguments that failed the
strict tool protocol. The adapter had dropped native tool-call IDs. General ID propagation,
explicit terminal-tool wording and bounded unload waiting were subsequently fixed for all
models, with new frozen exact synthetic inputs and a full common rerun. Results here are
preserved failures/provenance, not selected final-comparison performance or a claim about
Mistral's underlying reasoning ability. Source snapshots are archival, not product entrypoints.
