"""dbt-core artifact parser — the first plugin of the framework.

Importing this package registers :class:`DbtArtifactParser` with the shared
:data:`~artifact_parser.core.registry.registry`, so ``registry.parse(blob)``
works as soon as ``artifact_parser`` is imported.

The version-dependent code (the typed models, the schema-version lookup table,
and the ``parse_*`` dispatch) is generated and lives under
:mod:`artifact_parser.dbt.generated` — a directory you can delete and rebuild
with ``codegen dbt``. The public ``parse_*`` names are re-exported here so that
import path never changes.
"""

from artifact_parser.core.registry import registry
from artifact_parser.dbt.generated.parser import parse_catalog
from artifact_parser.dbt.generated.parser import parse_manifest
from artifact_parser.dbt.generated.parser import parse_run_results
from artifact_parser.dbt.generated.parser import parse_sources
from artifact_parser.dbt.plugin import DbtArtifactParser

dbt_parser = DbtArtifactParser()
registry.register(dbt_parser)

__all__ = [
    "DbtArtifactParser",
    "dbt_parser",
    "parse_catalog",
    "parse_manifest",
    "parse_run_results",
    "parse_sources",
]
