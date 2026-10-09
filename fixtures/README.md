# Fixtures

`safe/findings.sarif` and `vulnerable/findings.sarif` are hand-authored examples used by the quick start.

`vulnerable/findings.zizmor-1.30.1.sarif` is captured output from zizmor 1.30.1 against the unchanged vulnerable workflow. It retains the actual tool metadata, rule IDs, locations and code-flow structure. Generate it in an isolated directory so paths refer to the fixture root:

```sh
mkdir -p /tmp/sentinel-fixture/.github/workflows
cp fixtures/vulnerable/.github/workflows/review.yml /tmp/sentinel-fixture/.github/workflows/
cd /tmp/sentinel-fixture
zizmor --offline --persona=pedantic --format=sarif . > findings.sarif
```

The pedantic persona includes the excessive-permissions finding. The default persona reports the template-injection and dangerous-triggers findings for this workflow. Other reported rules remain unsupported by Sentinel and produce abstentions.

`repairable/findings.zizmor-1.30.1.sarif` is captured default-persona output against the
explicit-Bash printf fixture. `repairable/expected-fixed.yml` records the proposed source.
`repairable/fixed.findings.zizmor-1.30.1.sarif` captures the scanner rerun after applying the
preview diff in an isolated copy: one template-injection finding before, zero findings after.
Only static parsing/scanning was performed. Reproduce by copying either workflow to an isolated
`.github/workflows/review.yml`, running zizmor 1.30.1 from that root with
`--offline --format=sarif .`, and comparing its results.
