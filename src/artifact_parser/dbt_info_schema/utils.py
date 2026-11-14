"""Helpers for reading the info-schema version out of a table dict."""

from artifact_parser.core.base import BaseArtifactModel
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.dbt_info_schema.generated.models.info_schema_v1 import InfoSchemaV1

PROJECT_TABLE = "dbt.project"

#: ``dbt.project.schema_version`` -> model. Add a row per new parquet layout.
VERSION_MODELS: dict[int, type[BaseArtifactModel]] = {1: InfoSchemaV1}


def get_info_schema_version(artifact: dict) -> int:
    """Return ``schema_version`` from the ``dbt.project`` table.

    Raises:
        UnknownArtifactError: if the table or its row is missing. A missing
            ``schema_version`` comes back as ``None``, which
            :func:`get_model_class` rejects.
    """
    rows = artifact.get(PROJECT_TABLE)
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise UnknownArtifactError(f"{PROJECT_TABLE!r} table is missing or empty.")
    return rows[0].get("schema_version")


def get_model_class(schema_version: int) -> type[BaseArtifactModel]:
    """Return the model class for ``schema_version``.

    Raises:
        UnknownArtifactError: if no known layout matches.
    """
    try:
        return VERSION_MODELS[schema_version]
    except (KeyError, TypeError) as exc:
        raise UnknownArtifactError(
            f"Unknown info schema version: {schema_version!r}"
        ) from exc
