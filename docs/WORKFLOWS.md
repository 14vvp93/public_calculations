# Workflow catalog

## Public compute repository

| Workflow | Trigger | Purpose | Writes |
|---|---|---|---|
| `compute.yml` | Reusable call / manual dispatch / approval-marker push | Archive inventory, safe split-ZIP extraction, audio inventory | Actions artifact only |
| `import-public-firmware.yml` | Manual dispatch / approval marker on main | Import approved public firmware from `14vvp93/mt8163_audio_engine` | Commits approved firmware and SHA-256 manifest to public main |
| `validate-infrastructure.yml` | Push / pull request | Validate workflow YAML, Python scripts and tests | No repository writes |

## Primary repository entry point

| Workflow | Trigger | Purpose | Writes |
|---|---|---|---|
| `run-public-compute.yml` | Manual dispatch | Call the reusable worker in `14vvp93/public_calculations` | Worker artifact attached to the caller run |

## Operating rules

- Use the primary repository as the operator-facing entry point.
- Dispatch expensive compute explicitly; do not run full firmware analysis for ordinary
  source-code edits.
- Validation is lightweight and must not unpack full firmware archives.
- The worker does not commit generated reports automatically.
- Artifacts are temporary; durable findings are reviewed before promotion.
- All workflows use least-privilege permissions and bounded runtime.
