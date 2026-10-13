# Fresh synthetic contract holdout

Six exact variants in affected categories were frozen before any model execution in commit
463697f. A manually found job-permission SARIF location was corrected pre-run in d4cf925 without
changing source or expected outcome. FREEZE.json records the preparation-time hash and zero
prior model runs; it is not a mutable current run counter.

The first actual local model execution passed 6/6 and is retained separately. See
[contract investigation](../../docs/CONTRACT_INVESTIGATION.md) for results and limitations.
Self-authored cases with implementation knowledge in known categories are not independent or
blind evidence. Subsequent model runs of these cases are regressions, never new holdout evidence.

```sh
python model_evaluation/run_local.py --model qwen3.8:27b-q4_K_M \
  --manifest model_evaluation/holdout-v2/manifest.json \
  --scanner /absolute/path/to/zizmor --output /tmp/sentinel-heldout-regression-unique.json
```

This command now reruns already-exposed cases. Do not relabel it first-use. The fixed labels,
source, region/candidate checks and request budgets apply; no fixture-specific production logic
or post-outcome label change was introduced. First-run output/checksums are immutable archives.
