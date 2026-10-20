# Workflow Sentinel

Workflow Sentinel investigates supplied [zizmor](https://docs.zizmor.sh/) findings in GitHub
Actions workflows. It resolves local source evidence, produces cited review packets, previews
a narrow class of Bash injection repairs, and validates eligible candidates on isolated copies.
An optional local Ollama agent selects bounded tools; the deterministic checks govern every
proposal and validation. Source workflows are never executed or automatically patched.

## Install

Requires Python 3.11+ on Linux or macOS. The offline CLI and local adapter require only PyYAML.

```sh
git clone https://github.com/Shanmukha-Y/workflow-sentinel.git
cd workflow-sentinel
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m pip install zizmor==1.30.1
```

The scanner must be a trusted native zizmor 1.30.1 binary outside the repository being reviewed.
For external targets, keep the installed scanner outside that target checkout. Ollama is
installed separately; this project never starts a server, downloads weights automatically,
reads model credentials, or falls back to cloud inference.

## Review a workflow

Try the included **synthetic input**, not a real incident:

```sh
workflow-sentinel --sarif fixtures/vulnerable/findings.sarif \
  --repo fixtures/vulnerable > report.json
```

The default is an actual deterministic source investigation, with no LLM. Reports contain file
hashes, source excerpts/ranges, YAML context, reasons and citations. Supported rules are
`template-injection`, `excessive-permissions`, and `dangerous-triggers`. Unknown rules or missing/
ambiguous evidence abstain. A review is advisory: exploitability is not established.

For your own checkout, generate SARIF at its root, then review the same revision:

```sh
zizmor --offline --format=sarif . > findings.sarif
workflow-sentinel --sarif findings.sarif --repo . > report.json
```

Reports include unredacted source excerpts. Review them for sensitive content before sharing
or permitting a model to receive them. The accepted subset and report format are in [schemas](schemas).

## Repair preview and static validation

```sh
workflow-sentinel --sarif fixtures/repairable/findings.zizmor-1.30.1.sarif \
  --repo fixtures/repairable --preview-repairs > preview.json
workflow-sentinel --sarif fixtures/repairable/findings.zizmor-1.30.1.sarif \
  --repo fixtures/repairable --validate-repairs \
  --scanner "$(command -v zizmor)" > validation.json
```

Supported repairs move one allowlisted untrusted expression from a literal Bash `printf` into
an intermediate environment variable and a quoted shell expansion. An explicit `shell: bash`,
matching snippet/hash and unambiguous context are required. Existing environments, defaults,
containers, collisions, extra commands and unsupported syntax refuse. Permission requirements
cannot be inferred; permission repair is not implemented. Checkout/trigger changes are report-only.

Validation reconstructs the allowed edit, checks hashes/YAML, and runs fixed offline scanner
arguments on before/after copies of the single workflow. It confirms target removal and rejects
new/strengthened findings. Results are `validated`, `rejected`, `unsupported`, or `unavailable`.
Review the diff and source hash before applying anything yourself. A static pass is not proof
of security or runtime semantic equivalence.

## Real local agent and featured demo

Use an already installed tool-capable local model with Ollama listening on loopback. For example:

```sh
OLLAMA_HOST=127.0.0.1:11434 ollama pull qwen3.8:27b-q4_K_M
python examples/review_demo.py --local-model qwen3.8:27b-q4_K_M \
  --scanner "$(command -v zizmor)" --output-directory /tmp/sentinel-real-demo
```

The featured demo **actually calls the local model and real scanner**. It writes review,
preview, agent/validation and unchanged-source-hash artifacts. The output directory must be new.
There is no canned model-output fallback. It uses one labeled synthetic workflow.

The local endpoint is fixed to `127.0.0.1:11434`; proxies/redirects and cloud tags/remote metadata
are refused. Locally installed GGUF/tool-capable Qwen, Gemma and Mistral Small families are
accepted by the adapter; Mistral remains experimental because of measured strict-format
failures. Model requests are checked against advertised prerequisites and eligible packet
indices, then independently checked by the controller. Unsupported repair can finish a manual
review; insufficient evidence or failed validation abstains. No commands, paths, arbitrary
patches or model security verdicts are accepted. [Contract and threat model](docs/THREAT_MODEL.md).

## Measured evaluations

[The local comparison](comparison/REPORT.md) contains actual inference records, a frozen protocol,
synthetic case definitions and repeated trials. The older eight cases are development data;
the earlier six-case holdout is now exposed data. Fresh first-exposure results and repeated
exposed trials are separated. These self-authored cases are not real incidents, independent
blind data, vulnerability detection, or a broad security/model-reliability benchmark.

The original Qwen run scored 4/8 and remains preserved. General review/repair contract fixes
then passed those eight as development regressions and six fresh variants. [Failure investigation](docs/CONTRACT_INVESTIGATION.md).
Historical mock/model-oracle records are kept only as explicitly labeled test-harness provenance
under `tests/archives`; they are never model-performance evidence. Unit tests use controlled
transports for protocol/scoring/failure paths. Synthetic input fixtures are separate from actual
model measurements. [Product/test audit](docs/PRODUCT_AUDIT.md).

## Limits

The agent selects among tightly guided evidence/propose/validate/finish/abstain tools; it does
not independently discover vulnerabilities or evaluate workflow conditions/permission needs.
Investigation is bounded to 32 files, 4 MB total, 1 MB/file and 1,000 findings, with YAML node/
depth/context bounds. Unsafe paths, symlinks, ambiguous locations and unsupported YAML abstain.
Matched source hashes/snippets establish local correspondence, not authenticated scan provenance.

Agent sessions allow eight turns, bounded input/output and two validation pairs without retries.
Native inference uses an 8K context, 256-token output cap and a 15-second call deadline. Each
scanner call is capped at 15 seconds, 1 MB stdout and 64 KB stderr. Evaluation adds aggregate
caps. Trusted dependencies, the local daemon and native scanner are not OS-sandboxed. Raw evidence
capture is opt-in, intended for the audited synthetic evaluation; ordinary traces avoid raw
provider bodies. See [adapter details](docs/ADAPTER.md) and [evaluation methods](model_evaluation/README.md).

The optional OpenAI SDK adapter has protocol tests but **no real cloud-model evaluation**. It
requires an externally supplied approved client/model/disclosure configuration; no cloud use or
credentials are automatically enabled. Install `.[provider]` only if using that API. Local results
do not establish its effectiveness. Byte/token/request caps are not monetary or retention guarantees.

## Development and license

```sh
python -m pip install -e '.[dev]'
python scripts/check_test_budget.py
python -m unittest discover -s tests -v
ruff check .
mypy src
```

[MIT](LICENSE). Separately installed tools, dependencies and weights retain their own terms;
none is vendored. [Dependency scope](docs/DEPENDENCIES.md), [release audit](docs/RELEASE_READINESS.md).

The maintained unit suite is capped at 50 collected cases. See
[the coverage inventory](docs/TEST_COVERAGE.md) for retained boundaries and deliberate gaps.
