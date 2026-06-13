<!-- Thanks for the PR! Fill in what's relevant and delete what isn't. -->

## Summary

<!-- What does this change do, and why? Link any related issue. -->

Closes #

## Type of change

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] New plugin or artifact family
- [ ] New schema version for an existing artifact
- [ ] Breaking change (existing behaviour changes)
- [ ] Codegen / template change (regenerates files under `generated/`)
- [ ] Docs / CI / tooling only

## Checklist

- [ ] `task lint` passes (`ruff format` + `ruff check`)
- [ ] `task test` passes at 100% coverage
- [ ] Imports are at module top, no relative imports, one class per file
- [ ] I did **not** hand-edit anything under `dbt/generated/` (regenerated via `task codegen` instead)
- [ ] If generated output changed, I ran `task codegen` and committed the result (the CI in-sync gate will check this)
- [ ] Tests added/updated for the change (real-artifact round-trips in `tests/data/` if relevant)
- [ ] Docs updated (README / CLAUDE.md) where behaviour or layout changed

## Notes for reviewers

<!-- Anything non-obvious: trade-offs, follow-ups, things you're unsure about. -->
