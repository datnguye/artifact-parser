"""Helpers for reading the dbt schema version out of an artifact dict."""

from artifact_parser.core.base import BaseArtifactModel
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.dbt.generated.version_map import ArtifactTypes


def get_dbt_schema_version(artifact: dict) -> str:
    """Return ``metadata.dbt_schema_version`` from a dbt artifact dict.

    Raises:
        UnknownArtifactError: if the metadata block or the version is missing.
    """
    if "metadata" not in artifact:
        raise UnknownArtifactError("'metadata' is missing from the artifact.")
    if "dbt_schema_version" not in artifact["metadata"]:
        raise UnknownArtifactError("'metadata.dbt_schema_version' is missing.")
    return artifact["metadata"]["dbt_schema_version"]


def get_artifact_type(schema_version: str) -> ArtifactTypes:
    """Return the :class:`ArtifactTypes` member for ``schema_version``.

    Raises:
        UnknownArtifactError: if no known artifact type matches.
    """
    for artifact_type in ArtifactTypes:
        if schema_version == artifact_type.value.dbt_schema_version:
            return artifact_type
    raise UnknownArtifactError(f"Unknown dbt schema version: {schema_version}")


def get_model_class(schema_version: str) -> type[BaseArtifactModel]:
    """Return the model class for ``schema_version``.

    Raises:
        UnknownArtifactError: if no known artifact type matches.
    """
    return get_artifact_type(schema_version).value.model_class
