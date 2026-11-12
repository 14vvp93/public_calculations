# Compute worker contract

## Purpose

This repository is the public, resource-intensive worker for
`14vvp93/mt8163_audio_engine`. It processes public firmware inputs and publishes
reproducible reports. It is not a second product source repository.

## Invocation

The initial worker is started manually with `workflow_dispatch`. Its `task`
input selects a bounded operation:

- `inventory`: hash and inventory supported firmware archives.
- `extract`: safe extraction into a temporary workspace and manifest generation.
- `elf-audit`: inspect ELF files when the required host tools are available.
- `all-light`: run inventory and static repository checks without committing output.

Heavy jobs must not run on every push. Use explicit dispatch and concurrency groups.
Inputs are untrusted strings: validate choices, reject path traversal, and never evaluate
input as shell code.

## Inputs and outputs

- Inputs are public archives or repository paths under `firmware/`.
- Raw input bytes are immutable. The worker computes SHA-256 before processing.
- Outputs include JSON manifests, text reports, and Actions artifacts.
- Every report records source hashes, tool versions, task name, and completion status.
- Partial or failed extraction must be marked incomplete and must not be presented as
  a complete firmware inventory.

## Security

This repository is public. Firmware dumps and extracted firmware contents are approved
for public storage, but credentials, tokens, passwords, private signing keys, personal
data, and unrelated private material are not. Logs and artifacts are public too.
Never echo secrets. Use the minimum token permissions and do not expose write tokens
to code from untrusted pull requests.

The initial workflows need no secrets and use read-only repository permissions.
A future cross-repository publisher must be added only when required, with a narrowly
scoped credential stored as a GitHub Actions secret and protected from untrusted code.

## Reliability

- Pin third-party Actions to reviewed full commit SHAs before production use.
- Pin Python and analysis-tool versions.
- Use explicit timeouts and concurrency cancellation for duplicate runs.
- Upload intermediate artifacts with a documented retention period.
- Do not silently push generated files to the product repository.
- Promotion into the canonical repository requires review and a source commit/hash.
