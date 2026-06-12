"""Tests for the dbt public parser API and the framework plugin."""

import pytest

from artifact_parser import parse
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.dbt import dbt_parser
from artifact_parser.dbt.generated.models.catalog.catalog_v1 import CatalogV1
from artifact_parser.dbt.generated.models.manifest.manifest_v12 import ManifestV12
from artifact_parser.dbt.generated.models.run_results.run_results_v6 import RunResultsV6
from artifact_parser.dbt.generated.models.sources.sources_v3 import SourcesV3
from artifact_parser.dbt.generated.parser import parse_catalog
from artifact_parser.dbt.generated.parser import parse_catalog_v1
from artifact_parser.dbt.generated.parser import parse_manifest
from artifact_parser.dbt.generated.parser import parse_manifest_v1
from artifact_parser.dbt.generated.parser import parse_manifest_v12
from artifact_parser.dbt.generated.parser import parse_run_results
from artifact_parser.dbt.generated.parser import parse_run_results_v6
from artifact_parser.dbt.generated.parser import parse_sources
from artifact_parser.dbt.generated.parser import parse_sources_v3


def test_parse_catalog_generic(catalog_v1: dict) -> None:
    assert isinstance(parse_catalog(catalog_v1), CatalogV1)


def test_parse_catalog_v1(catalog_v1: dict) -> None:
    assert isinstance(parse_catalog_v1(catalog_v1), CatalogV1)


def test_parse_manifest_generic(manifest_v12: dict) -> None:
    assert isinstance(parse_manifest(manifest_v12), ManifestV12)


def test_parse_manifest_v12(manifest_v12: dict) -> None:
    assert isinstance(parse_manifest_v12(manifest_v12), ManifestV12)


def test_parse_run_results_generic(run_results_v6: dict) -> None:
    assert isinstance(parse_run_results(run_results_v6), RunResultsV6)


def test_parse_run_results_v6(run_results_v6: dict) -> None:
    assert isinstance(parse_run_results_v6(run_results_v6), RunResultsV6)


def test_parse_sources_generic(sources_v3: dict) -> None:
    assert isinstance(parse_sources(sources_v3), SourcesV3)


def test_parse_sources_v3(sources_v3: dict) -> None:
    assert isinstance(parse_sources_v3(sources_v3), SourcesV3)


def test_generic_parser_wrong_family_raises(catalog_v1: dict) -> None:
    with pytest.raises(UnknownArtifactError, match="Not a dbt manifest artifact"):
        parse_manifest(catalog_v1)


def test_version_pinned_wrong_version_raises(manifest_v12: dict) -> None:
    with pytest.raises(UnknownArtifactError, match="Expected MANIFEST_V1 "):
        parse_manifest_v1(manifest_v12)


def test_generic_parser_unknown_schema_raises() -> None:
    bogus = {"metadata": {"dbt_schema_version": "made-up/v1.json"}}
    with pytest.raises(UnknownArtifactError, match="Not a dbt catalog artifact"):
        parse_catalog(bogus)


def test_plugin_can_parse(manifest_v12: dict) -> None:
    assert dbt_parser.can_parse(manifest_v12) is True


def test_plugin_can_parse_rejects_unknown() -> None:
    assert dbt_parser.can_parse({"metadata": {"dbt_schema_version": "x"}}) is False


def test_plugin_can_parse_rejects_no_metadata() -> None:
    assert dbt_parser.can_parse({}) is False


def test_plugin_parse(manifest_v12: dict) -> None:
    assert isinstance(dbt_parser.parse(manifest_v12), ManifestV12)


def test_registry_parse_routes_to_dbt(sources_v3: dict) -> None:
    assert isinstance(parse(sources_v3), SourcesV3)
