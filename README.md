# Workflow Sentinel

Workflow Sentinel turns [zizmor](https://docs.zizmor.sh/) findings into JSON reports for reviewing GitHub Actions workflows. It connects each finding to local source evidence and adds remediation guidance with links to the relevant documentation.

It currently supports three zizmor rules:

- `template-injection`: untrusted expressions used in script contexts.
- `excessive-permissions`: overly broad workflow or job token permissions.
- `dangerous-triggers`: privileged triggers that need closer review, including possible untrusted checkout.

Reports include review decisions, source paths and lines, excerpts, file hashes, and guidance where evidence is available. Findings with missing evidence or unsupported rules are marked `abstain` with a reason. Patch generation is planned; the current tool helps prepare findings for human review.

## Install

Requires Python 3.11 or later. From the repository root:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Quick start

Try the included example:

```sh
workflow-sentinel \
  --sarif fixtures/vulnerable/findings.sarif \
  --repo fixtures/vulnerable > report.json
```

This produces three entries: an expression embedded in a shell command, `write-all` token permissions, and a privileged trigger with a pull request checkout. The fixtures use hand-authored SARIF to demonstrate the report format. See [the example report](examples/offline-report.json) for the full output.

For your own repository, [install zizmor](https://docs.zizmor.sh/installation/) and generate SARIF first:

```sh
cd /path/to/repo
zizmor --offline --format=sarif . > findings.sarif
workflow-sentinel --sarif findings.sarif --repo . > report.json
```

Run zizmor from the repository root so source paths are relative to `--repo`. Sentinel expects SARIF 2.1.0 and the unprefixed rule IDs listed above. zizmor 1.30.1 emits `zizmor/` prefixes; those findings currently receive `abstain` unless their IDs are normalized. It writes JSON to stdout and errors to stderr. Exit code `0` means the report was generated, including any findings; `2` indicates invalid input.

## Limitations

A `review` decision means the finding's source locations resolved, not that exploitability was confirmed. Sentinel does not independently scan workflows, and an empty report does not establish security.

Use the same stable checkout that was scanned. File hashes identify the current source; Sentinel cannot yet verify that it matches the revision used to produce the SARIF. Reports include source excerpts, so check for sensitive content before sharing.

Inputs are limited to 1 MB per file, 1,000 findings, and 10 locations per finding. Remote paths, paths outside the repository, and SARIF URI base references are unsupported. The [schemas](schemas) describe the accepted input subset and report format.

## Development

```sh
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
ruff check .
mypy src
```

See [ROADMAP.md](ROADMAP.md) for planned investigation, repair, and validation work.
