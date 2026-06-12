"""Locate the dbt plugin's on-disk directories that codegen writes into.

Paths are derived from the *imported* :mod:`artifact_parser` package rather than
assumed relative to this file, so the CLI works the same from a source checkout
or an editable install. Importing the top package is safe even when the
generated code is missing — its dbt import is guarded — so codegen can rebuild a
dropped ``generated/`` directory from scratch.
"""

from pathlib import Path

import artifact_parser

PACKAGE_DIR = Path(artifact_parser.__file__).resolve().parent
DBT_DIR = PACKAGE_DIR / "dbt"
RESOURCES_DIR = DBT_DIR / "resources"

GENERATED_DIR = DBT_DIR / "generated"
MODELS_DIR = GENERATED_DIR / "models"
VERSION_MAP_PATH = GENERATED_DIR / "version_map.py"
PARSER_PATH = GENERATED_DIR / "parser.py"
GENERATED_INIT_PATH = GENERATED_DIR / "__init__.py"

# The discovered version table lives in the codegen package itself (next to this
# file), not in the runtime package — it is codegen's own input.
VERSIONS_PATH = Path(__file__).resolve().parent / "versions.py"
