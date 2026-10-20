# Maintained test coverage

2026-10-20 cleanup: **117 → 50 collected unittest cases**. The original count was
117 methods, with additional bundled input variants; the retained suite has no
parameterized cases or subtests. No cases were moved to benchmarks or hidden from
discovery. Removed code remains available in Git history.

| Module | Before methods | After cases |
|---|---:|---:|
| `cli` | 13 | 8 |
| `investigation` | 16 | 8 |
| `repairs` | 10 | 7 |
| `validation` | 15 | 8 |
| `agent` | 12 | 6 |
| `openai_adapter` | 8 | 3 |
| `ollama_adapter` | 16 | 4 |
| `demo` | 1 | 1 |
| `model_evaluation` | 18 | 2 |
| `comparison_records` | 4 | 2 |
| `evaluation` | 4 | 1 |

Selection favors security boundaries over duplicate happy paths and bookkeeping:

- Offline CLI determinism/schema, safe input, stale lines, encoded traversal,
  symlinks, file/result bounds and real CLI execution.
- YAML context/citations, stale snippets and hashes, duplicate keys/depth limits,
  failed-read accounting and one snapshot for repeated locations.
- Real SARIF repair/diff roundtrip and source immutability, literal argument
  preservation, redirection/environment/path refusals, checkout report-only.
- Disposable static validation, tampered diff/new finding rejection, candidate
  budget, native scanner trust boundary, fixed argv/environment and process timeout.
- Host-controlled agent flow, validated proposal, unvalidated completion refusal,
  shell-tool rejection, evidence abstention, duplicate JSON and trace sanitization.
- OpenAI wire roundtrip, no retry/error disclosure, wall deadline; local protocol,
  host-state tool exposure, failed-validation gate and call-ID continuity.
- Existing-output demo preflight, scoring failures, frozen dataset integrity,
  complete actual comparison provenance and reproducible derived failure counts.

Removed redundant families include broad malformed-input permutations, secondary
URI/YAML/column encodings, every shell spelling, permission-format variants,
provider configuration/status permutations, detailed usage/budget bookkeeping,
and duplicate archived-record assertions. These are deliberate regression gaps:
fewer tests can miss failures previously covered. In particular, wrapper scanners,
new/strengthened duplicate findings, all source-hash tamper fields, local remote-model
metadata rejection, and all provider response limits no longer each have a dedicated
case. The implementation still enforces those checks; this cleanup does not establish
that they are secure. Replacement scenarios should displace a lower-priority case.

Production code, frozen inputs, measured model results and raw evidence are unchanged.
Existing published evaluation datasets are historical/reproducibility assets, not a
place to relocate removed unit cases. No new inference was run for this cleanup.
Artifact-integrity tests iterate records of one saved experiment; protocol tests may
inspect successive messages in one conversation. Neither generates input variants.

`python scripts/check_test_budget.py` uses normal unfiltered unittest discovery,
requires declared/collected counts to agree, rejects common subtest/decorator/skip
and custom-discovery shortcuts, and enforces 1–50. It cannot detect every semantic
omnibus test: reviewers must keep independently varied scenarios in separate tests.
CI runs the guard, all cases, formatting for maintained tests/guard, lint/type checks,
static fixture regression and distribution checks. Passing checks do not prove security.
