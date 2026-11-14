"""Read a dbt ``info_schema/v1`` parquet directory into plain row dicts.

Needs the optional ``info-schema`` extra (``pyarrow``). Everything else in the
package works without it; only calling these functions raises when it is absent.
"""

from pathlib import Path

from artifact_parser.core.exceptions import OptionalDependencyError
from artifact_parser.dbt_info_schema.generated.models.info_schema_v1 import InfoSchemaV1
from artifact_parser.dbt_info_schema.plugin import DbtInfoSchemaParser

try:
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - exercised by patching ``pq`` to None
    pq = None

#: ``dbt_internal.*`` is explicitly not part of dbt's public contract.
PUBLIC_PREFIXES = ("dbt.", "dbt_rt.")


def load_info_schema(path: str | Path) -> dict[str, list[dict]]:
    """Return ``{"dbt.models": [row, ...], ...}`` for every public table in ``path``.

    Raises:
        OptionalDependencyError: if ``pyarrow`` is not installed.
    """
    if pq is None:
        raise OptionalDependencyError(
            "Reading the info schema needs pyarrow: "
            "pip install 'artifact-parser[info-schema]'."
        )
    return {
        file.stem: pq.read_table(file).to_pylist()
        for file in sorted(Path(path).glob("*.parquet"))
        if file.stem.startswith(PUBLIC_PREFIXES)
    }


def parse_info_schema(path: str | Path) -> InfoSchemaV1:
    """Load ``path`` and parse it into the versioned model.

    Raises:
        OptionalDependencyError: if ``pyarrow`` is not installed.
        UnknownArtifactError: if the ``schema_version`` is missing or unknown.
    """
    return DbtInfoSchemaParser().parse(load_info_schema(path))
