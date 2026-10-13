# Product behavior and test-evidence audit

The repository includes synthetic input fixtures and legitimate controlled unit-test transports.
It is not accurate to say that every file is an actual model run. Product/performance paths are
distinguished here so those test mechanisms cannot be mistaken for capability evidence.

## Findings and changes

Earlier versions exposed a scripted `--agent-script` replay, featured a mock SDK demo, and used
scripted replay as the consolidated demo's default. These were harness exercises, not live
reasoning. They have been removed from current product/demo paths. The product `agent.run`
entry point requires a configured adapter; its private execution seam supports controlled unit
tests only. The featured consolidated demo now requires a local model and actually invokes
Ollama and native zizmor. It has no scripted/canned-response fallback. The ordinary offline CLI
still performs real deterministic file investigation and optional real scanner validation; it
does not pretend to be model reasoning.

Mock factories and scripted structural inputs are under `tests/helpers`. Historical mock oracle
records are under `tests/archives/model-harness-validation`, with original bytes/checksums and
history preserved. They verify harness bookkeeping/scoring and error handling, not performance.
Unit mocks remain for success/error protocol roundtrips, scoring invariants and failure-path
coverage. CI cannot run local models; it does not substitute mocks for reported model results.
No prerecorded model output is used by the comparison runner.

## Actual measurements and allowed synthetic data

Every published comparison performance record comes from the frozen runner calling native local
Ollama inference on installed weights. Bounded raw requests/responses, token counts, per-attempt
status/timing and sampled model residency are retained. Synthetic workflows/SARIF are explicit
inputs, not real incidents. They contain symbolic event expressions, not fetched private issue
text. Labels/goldens are not passed to the model. No credential or private target repository is
used. Failed/unknown attempts and skipped cases are not removed from denominators.

Synthetic unit fixtures and historical test artifacts remain intentionally non-real input/test
data. Claims based on those files must remain labeled test-harness verification. Actual baseline
failures and later genuine runs are preserved separately. No broad model reliability, real-world
security effectiveness, independent-blind evaluation or vulnerability-detection claim follows.

## API examples

Library integrations necessarily accept caller-supplied inputs/configuration; they are not
standalone runnable scripts or hidden stub implementations. The local CLI/demo is the supported
credential-free executable path. OpenAI requires an externally configured client and has only
mocked protocol tests, not real cloud capability results. No credential provisioning or live
cloud call was performed. Dependency tests' fixed mock auth placeholders are non-credentials
and stay test-only. A blanket "no mocks anywhere" statement would be false.

## Remaining intentional test/non-inference structures

Synthetic workflows/SARIF and golden labels remain fictional inputs by design. Private typing
protocol declarations and a nonpersistent HTTP client's no-op close are not stubbed inference:
each actual request opens/closes its response context and the client owns no persistent pool.
Test-only controlled transports and historical oracle records remain, explicitly not real model
measurements. The featured demo and comparison use actual local calls; static example reports
are deterministic file/scanner outputs, not claimed LLM runs. Mistral's real residual formatting
failures are documented instead of replaced with canned completion. See comparison/REPORT.md.
