# Workflow catalog

| Workflow | Trigger | Purpose | Writes |
|---|---|---|---|
| `compute.yml` | Manual dispatch only | Run archive inventory and split-aware extraction | Actions artifact only |
| `import-public-firmware.yml` | Manual dispatch on main | Import owner-approved firmware from the private source repo | Commits firmware and SHA-256 manifest to public main |
| `validate-infrastructure.yml` | Push / pull request | Compile scripts and run unit tests | No repository writes |
| `validate-infrastructure.yml` | Pull request / push to main | Validate scripts and workflow structure | No repository writes |

## Operating rules

- Expensive analysis is opt-in and manually dispatched.
- Validation is lightweight and must not unpack full firmware archives.
- No workflow commits or pushes generated results automatically.
- Artifacts are temporary; durable findings are reviewed before committing.
- All workflows use least-privilege permissions and bounded runtime.
