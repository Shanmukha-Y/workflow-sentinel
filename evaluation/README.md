# Evaluation

The frozen suite contains 38 labeled synthetic cases: 18 development cases, 15 audited first-use holdout cases, and 5 reused regression cases. Labels and candidate source were specified before execution against production commit `d2fc6c6`. No production code was changed or tuned during these runs.

The author knew the implementation. The holdout consists of first-use input variants, not unseen branches, an independent blind study, or real-world vulnerabilities. Source/citation checks verify hashes, excerpts, labeled YAML routes and range bounds; they do not establish that every cited fact supports exploitability. Instruction-like comments are data tests, not model prompt-injection evaluations.

## Reproduce

From the repository root, with the development dependencies installed:

```sh
python evaluation/run.py \
  --scanner /absolute/path/to/zizmor \
  --output /tmp/sentinel-evaluation-regression.json
```

Use a trusted native zizmor 1.30.1 binary outside the target repository. Output files are created exclusively: existing results are never overwritten. Subsequent runs default to `regression`; they are not new held-out measurements. `--split development`, `--split holdout-first-use`, and `--split regression-reused` select the audited subsets.

Omit `--scanner` for offline triage, diff and source checks. Live validation then stays `not-run`, apart from preflight refusals and explicitly simulated scanner faults. Offline case accuracy only covers observed checks: read `validation_not_run` before comparing it with a live run.

The runner writes disposable synthetic workflows, produces previews, and applies diffs as data to a second disposable copy using fixed `git apply` arguments. It never executes workflow scripts. Real validation uses the bounded scanner runner; scanner-fault scenarios stub output and are reported separately. Original source must remain unchanged. The only external executable arguments are fixed developer-tool invocations; dataset text cannot supply commands.

## First-run results

| Measure | Development | Audited first-use holdout | Reused regressions |
|---|---:|---:|---:|
| Expected policy outcomes matched | 18/18 | 15/15 | 5/5 |
| Triage policy precision / recall | 12/12 / 12/12 | 7/7 / 7/7 | 5/5 / 5/5 |
| Repair eligibility precision / recall | 7/7 / 7/7 | 5/5 / 5/5 | 1/1 / 1/1 |
| Repair abstentions / finding decisions | 9/16 | 9/14 | 4/5 |
| Citation records passing source checks | 57/57 | 35/35 | 25/25 |
| Proposed diffs matching labeled candidate | 7/7 | 5/5 | 1/1 |
| Original sources unchanged | 18/18 | 15/15 | 5/5 |
| Actual live scanner validation agreement | 2/2 | 4/4 | 0/0 |
| Simulated scanner fault agreement | 5/5 | 0/0 | 1/1 |

A `0/0` ratio is unavailable, not 100%. Precision/recall here concern *triage and repair policy labels*, not vulnerability detection. Sentinel consumes SARIF; these metrics do not measure scanner recall or general security effectiveness. Repair validity means exact labeled YAML plus successful diff application, not runtime semantic equivalence. Citation records are not unique facts.

Six eligible workflows received two real scans each (12 calls total), and all six matched their validation labels. One additional proposal was correctly rejected at preflight as unsupported because of a dynamic action reference; no scanner ran for that case. Six controlled scanner-fault scenarios exercised regressions, retained/missing targets, malformed output and line shifts. They are not real-scanner results. No production outcome failures were observed in this suite.

## Original records and corrections

- [Frozen manifest](manifest.json), [freeze checksum](FREEZE.json), and [classification audit](AUDIT.json).
- [Original development run](results/first-run-development.json) and [original initially named holdout run](results/first-run-holdout.json) remain intact.
- [Audited first-run summary](results/first-run-audited-summary.json) is the result table's source; it reclassifies five prior-tested variants as reused regressions. The original file's 20-case holdout claim should not be used.
- The original holdout report counted a zero-attempt preflight refusal as live validation, reporting 5/5. Correct attribution is **4/4 actual scanner comparisons plus 1/1 preflight refusal**. The raw error is preserved; the runner and summary correct it.
- [Regression after the audit](results/regression-after-audit.json) matched 38/38 labels. It is a rerun, not another first-use holdout.

The echo source location was corrected during label review before any run (`997b3c7`). Later corrections concern subset classification and measurement attribution, not production behavior or expected outcome labels. Raw first-run checksums are kept in [HISTORY.json](HISTORY.json).

The suite is small, synthetic and aligned with a narrow allowlist. Successful refusals can dominate aggregate accuracy; unsupported patterns are not repaired. No held-out tuning was performed, and no paid or live model reasoning was evaluated. New production changes should be checked with regression runs and a separately frozen new first-use set if fresh holdout evidence is needed.
