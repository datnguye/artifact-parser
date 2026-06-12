"""Tests for the dbt schema-version helpers."""

import pytest

from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.dbt.generated.models.manifest.manifest_v12 import ManifestV12
from artifact_parser.dbt.generated.version_map import ArtifactTypes
from artifact_parser.dbt.utils import get_artifact_type
from artifact_parser.dbt.utils import get_dbt_schema_version
from artifact_parser.dbt.utils import get_model_class
from tests.conftest import MANIFEST_V12_URL


def test_get_dbt_schema_version(manifest_v12: dict) -> None:
    assert get_dbt_schema_version(manifest_v12) == MANIFEST_V12_URL


def test_get_dbt_schema_version_missing_metadata() -> None:
    with pytest.raises(UnknownArtifactError, match="'metadata' is missing"):
        get_dbt_schema_version({})


def test_get_dbt_schema_version_missing_version() -> None:
    with pytest.raises(UnknownArtifactError, match="dbt_schema_version' is missing"):
        get_dbt_schema_version({"metadata": {}})


def test_get_artifact_type() -> None:
    assert get_artifact_type(MANIFEST_V12_URL) is ArtifactTypes.MANIFEST_V12


def test_get_artifact_type_unknown() -> None:
    with pytest.raises(UnknownArtifactError, match="Unknown dbt schema version"):
        get_artifact_type("https://schemas.getdbt.com/dbt/manifest/v99.json")


def test_get_model_class() -> None:
    assert get_model_class(MANIFEST_V12_URL) is ManifestV12
