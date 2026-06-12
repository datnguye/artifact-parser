---
description: Regenerate the dbt artifact models from dbt-core schemas, then format and test.
---

Regenerate the generated dbt code (models, version_map.py, parser.py) from the
committed schemas, with an optional argument selecting the artifact/version
(e.g. `/codegen manifest v12`). Use `$ARGUMENTS` if provided, else regenerate all.

Steps:

1. Run codegen from the cached schemas (no network) unless the user asks for fresh
   schemas:

   ```
   uv run codegen dbt --skip-download $ARGUMENTS
   ```

   For fresh upstream schemas instead, drop `--skip-download` (optionally pass
   `--ref <dbt-core-ref>`).

2. Normalise the generated code:

   ```
   uv run ruff format . && uv run ruff check --fix .
   ```

3. Verify nothing broke:

   ```
   uv run pytest --cov=artifact_parser --cov=codegen --cov-fail-under=100 -q
   ```

Report which files changed (`git status --short src/artifact_parser/dbt/`) and
whether the suite still passes at 100%. Remember: never hand-edit the generated
files — change the template (`src/codegen/dbt/templates/`) or the spec
(`src/codegen/dbt/artifact_spec.py`) instead.
