# Threat model and release boundaries

Workflow Sentinel reviews supplied zizmor SARIF and local GitHub Actions YAML. It resolves
bounded evidence, proposes a narrow deterministic Bash repair and can statically compare
isolated workflow copies. Optional OpenAI and loopback-only Ollama adapters choose among those tools. It never runs
target workflows, repository scripts or model-supplied shell commands and never applies patches.

## Assets and trust boundaries

Source integrity, private workflow content, credentials, host resources, evaluation integrity
and API spending are the protected assets. Workflow/SARIF content and model output are untrusted.
The application, installed Python/SDK dependencies, configured client factory, native scanner,
Ollama daemon/model weights, host OS and GitHub CI are trusted. SDK and scanner execution is bounded but not an OS sandbox;
a compromised dependency or scanner is outside the implemented defenses.

Source readers reject unsafe paths/symlinks and use directory descriptors. YAML parsing rejects
ambiguous structures and imposes byte/node/depth/step limits. Matched hashes/snippets establish
local correspondence, not an authenticated scanning revision. Repairs require exact supported
syntax and a matching snapshot, and the reconstructed YAML tree must change only allowlisted
run/env fields. Scanner comparisons operate on isolated single-workflow copies with fixed
arguments and a scrubbed environment; they cannot prove runtime equivalence or security.

## Model and disclosure risks

Instruction-like text in source can try to change model behavior. The interpreter permits only
structured packet-index evidence/proposal/validation/finish requests or abstention, enforces
order/budgets, and accepts no paths, commands, patches or model security verdicts. Generated
repairs still come from deterministic policy. The model can nevertheless choose poor tools,
miss useful work or abstain too often. A known synthetic local Qwen run scored 4/8; this is narrow tool-loop evidence, not broad
effectiveness or an injection-resistance claim. The synthetic exposure check confirms payload inclusion only.

Provider access is opt-in with a trusted injected client, explicit model, token cap and source
disclosure approval. Reports and tool observations contain unredacted excerpts; sharing or
sending them can reveal private data. Source/credential discovery for model authentication is
not implemented. Raw provider errors/responses are excluded from traces/evaluation records;
SDK prompt history exists in process memory. Call cancellation and store=False do not establish
remote cancellation, zero charges or a retention promise. Resource caps are not monetary caps.

## Known capability limits

Permission repairs lack validated permission requirements; checkout/trigger changes stay
report-only. Repair support is a narrow literal printf pattern, not general Bash analysis.
Unknown findings and ambiguous evidence abstain. Validation supports one scanner version and
one-workflow comparisons; absent local action context can force unsupported outcomes. Empty
reports, review decisions, scanner success and schema validity are not security guarantees.

## Release gates

The original four failures are preserved; contract fixes passed 8/8 development and 6/6 fresh
synthetic cases, and a consolidated demo is verified. The standing instruction authorizes an
initial release after the final audit, scoped to narrow synthetic evidence, tightly guided tool
selection and untested broader/adversarial behavior. See CONTRACT_INVESTIGATION.md. Any OpenAI/cloud pilot still needs
separate approval.
Known synthetic regressions and SDK mocks remain separate from any future live results.
Public visibility follows the final readiness audit under the standing release authorization;
elapsed calendar time alone is not readiness. A later pilot must explicitly approve data disclosure, model, request scope
and a substantiated monetary ceiling. No deployment or social posting is performed by the implementation or evaluation.

The actual three-model comparison is documented in comparison/REPORT.md. Residual Mistral
protocol failures are safely refused, not coerced into success. Raw evidence is opt-in and used
only with audited synthetic data in that comparison; it requires review before sharing. No
canned model-output fallback remains in current product/demo paths. Unit mocks remain test-only.
