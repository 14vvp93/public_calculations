# Workflow catalog

| Workflow | Trigger | Purpose | Writes |
|---|---|---|---|
| `compute.yml` | Manual dispatch only | Run selected bounded analysis task | Actions artifact only |
| `validate-infrastructure.yml` | Pull request / push to main | Validate scripts and workflow structure | No repository writes |

## Operating rules

- Expensive analysis is opt-in and manually dispatched.
- Validation is lightweight and must not unpack full firmware archives.
- No workflow commits or pushes generated results automatically.
- Artifacts are temporary; durable findings are reviewed before committing.
- All workflows use least-privilege permissions and bounded runtime.
