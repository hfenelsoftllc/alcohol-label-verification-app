# .github

GitHub configuration for the repository.

- `CODEOWNERS` — review ownership per directory (enforced by branch protection).
- `workflows/ci.yml` — CI pipeline: tests, SAST (bandit), SCA (pip-audit),
  eslint-security, npm audit, and trivy image scan. Added in ISSUE 1.2.
