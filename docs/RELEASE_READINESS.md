# Initial release audit

The standing instruction authorizes public visibility when the project is genuinely ready.
No additional human-release gate is imposed. This release is a **bounded review prototype**,
scoped to its documented constraints and actual local measurements, not broad security/model
reliability. Optional Mistral remains experimental with measured strict-format failures.

| Gate | Evidence |
|---|---|
| Working source review/repair/validation | Unit suite, 38-case static regression, real native scanner runs |
| Genuine local capability | Preserved Qwen baseline/fix and actual three-model comparison with raw evidence |
| Failure preservation and fair comparison | Original failures, interrupted attempt, common corrected rerun, exposed/first/repeated roles |
| Reproducible install/demo | Clean package install, source/wheel asset/license checks; featured demo actually calls Ollama and scanner |
| Accurate natural README | Synthetic inputs labeled; no canned product/demo fallback; strict scope and backend limitations |
| License/dependencies | MIT project source, SPDX/wheel license, separately installed dependency/runtime/weight terms |
| Privacy/secrets/history | Full reachable-history and final-tree audit; generic resource details, no identifying local paths/user data |
| Publication | Change visibility only after final remote commit and exact CI pass; verify unauthenticated access |

Actual comparison results, category/error/latency/token/memory methods and limitations are in
[comparison/REPORT.md](../comparison/REPORT.md). Qwen/Gemma completed their tested tasks;
Mistral's ten final protocol failures were safely refused and remain failures. No observed
unauthorized validation/source mutations occurred in the 90 final case executions. None of
those facts proves security, statistical reliability or real-world effectiveness.

All performance measurements are actual on-device inference. Unit mocks remain under `tests`
for protocol/scoring/failure-path software verification, not capability evidence. Historical
mock/oracle files moved to a test-only archive with original bytes/checksums/history retained.
Synthetic fixtures are not real incidents. [Product audit](PRODUCT_AUDIT.md).

The featured demo requires a real local model and real scanner. The static CLI independently
performs actual file investigation/scanner checks without an LLM. No model weights, scanner
binaries or third-party libraries are vendored. No cloud calls, credential configuration,
deployments or social posting occurred. Native processes and local daemon are trusted rather
than OS-sandboxed. Future cloud/data/spend changes still need separate approval.

Hardware records contain generic CPU/RAM/software versions, model digests and measurement data;
no hostname, user-home path, device serial/UUID, process identity or private target content is
published. Commit identity is the intentionally public GitHub handle and noreply address.
Pattern/content/history review is not mathematical proof of absence; final checks cover only
this repository and published assets, not external credential stores or ignored environments.
