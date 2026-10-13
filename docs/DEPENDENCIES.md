# License and dependency scope

Workflow Sentinel's original source/documentation is under the [MIT license](../LICENSE).
The SPDX packaging metadata uses MIT and includes the license file in built distributions.
No third-party package, native binary, model weight or SDK source is vendored in this repository.
Dependencies keep their own copyright notices and licenses when installed separately.

Verified from installed distribution metadata and bundled license files for the pinned versions:

| Package | Role | License |
|---|---|---|
| PyYAML 6.0.3 | Required YAML parsing | MIT |
| OpenAI 3.29.0 | Optional provider SDK / mock protocol tests | Apache-2.0 |
| httpx2 2.13.1 | Development mock HTTP transport | BSD-3-Clause |
| Ruff 0.14.0 | Development lint | MIT; bundled notices apply |
| mypy 1.18.2 | Development typing | MIT |
| jsonschema 4.25.1 | Development schema validation | MIT |
| types-PyYAML 6.0.12.20260906 | Development typing | Apache-2.0 |

Only PyYAML is needed for the ordinary offline CLI and native loopback Ollama adapter.
The provider/dev extras install their pinned direct dependencies through the package manager;
transitive dependencies are not vendored or claimed to be covered by this project's MIT license.
This is a dependency/license inventory, not a vulnerability or supply-chain certification.

The optional trusted [zizmor](https://docs.zizmor.sh/) binary and [Ollama](https://ollama.com/)
are separately installed executables; Qwen weights are downloaded separately from the official
registry by the operator. None is bundled into source/wheel artifacts or relicensed by this
project. Model/runtime usage remains subject to the model/runtime's own distribution terms.
Pinned upstream GitHub Actions are referenced, not vendored. External documentation is linked,
not republished. Synthetic workflows/SARIF and evaluation labels were authored for this project.

Reproducibility is scoped to pinned direct dependencies, saved source/code hashes, model digest,
host/configuration records and explicit commands. Resolver/transitive package changes, engine
versions and hardware can change outcomes; inference bitwise determinism is not promised.
