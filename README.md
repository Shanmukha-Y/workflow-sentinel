# Workflow Sentinel

Day one of a seven-day GitHub Actions investigation and remediation agent.
**Today: deterministic offline SARIF triage, not live LLM reasoning or a security scanner.**
Consumes zizmor SARIF 2.1.0 and local YAML files. Emits cited review packets with line evidence
and SHA-256 hashes. Unsupported rules and missing evidence produce abstentions. It does not
independently detect vulnerabilities, establish exploitability, generate patches, or execute
workflows, target scripts, or model-generated commands. No network or model calls occur.

## Run (Python 3.11+)

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
workflow-sentinel --sarif fixtures/vulnerable/findings.sarif --repo fixtures/vulnerable
workflow-sentinel --sarif fixtures/safe/findings.sarif --repo fixtures/safe
python -m unittest discover -s tests -v
ruff check .
mypy src
```

The vulnerable demo yields three review packets. The mitigation demo yields zero because its
synthetic SARIF contains no findings. Zero packets does not prove safety. Fixtures are manually
constructed, not captured zizmor output or a held-out evaluation. Never execute these fixtures.
CI executes only this project's own tests and fixed development checks.

For real findings, independently install zizmor and run its static offline analyzer:
`zizmor --offline --format=sarif /path/to/repo > findings.sarif`. Sentinel never invokes it.
SARIF lines are one-based. Supported rule IDs: `template-injection`, `excessive-permissions`,
`dangerous-triggers` (report-only). All decisions need human review.

## Bounds and trust

Inputs are untrusted. Limits: 1 MB per file, 1,000 findings, 10 locations per finding, 500
characters per excerpt. Absolute/remote paths, traversal, escaping symlinks and unsupported
URI base resolution cannot supply evidence. Use a stable local checkout: the path check/open
has a race under concurrent hostile filesystem mutation. Hashes bind current source, not the
original scanned revision; stale SARIF may resolve to the wrong line. Day two must close that
gap. No YAML-aware context analysis yet. Reports may contain secrets from source excerpts:
inspect before sharing. SARIF messages are not copied. Errors exit 2; report generation exits
0 even with findings. Schemas describe the supported subset, not the entire SARIF standard.
Static checks do not prove security.

GitHub recommends intermediate environment variables for inline scripts, restricted token
permissions and avoiding privileged triggers with untrusted checkout. These are review guidance,
not universally safe rewrites. Sources verified 2026-10-08:

- [zizmor usage, offline mode, SARIF and limitations](https://docs.zizmor.sh/usage/)
- [zizmor audit rules](https://docs.zizmor.sh/audits/)
- [GitHub secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)

## Optional live adapter plan

Day six may add an opt-in adapter receiving bounded evidence and returning schema-validated
proposals. Offline remains default. No credentials or paid calls are needed now. Model output
is untrusted: no shell execution or document-directed tool expansion. Allowlist edits, validate
statically and require human review. Document provider, cost ceiling, redaction, timeout and
quality gates before enabling. See ROADMAP.md and PROGRESS.md. Keep private until release review.
