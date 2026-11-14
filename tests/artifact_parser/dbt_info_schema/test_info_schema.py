"""Tests for the dbt info-schema (parquet) plugin."""

from pathlib import Path

import pytest

from artifact_parser import parse
from artifact_parser.core.exceptions import OptionalDependencyError
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.core.registry import registry
from artifact_parser.dbt_info_schema import InfoSchemaV1
from artifact_parser.dbt_info_schema import load_info_schema
from artifact_parser.dbt_info_schema import loader
from artifact_parser.dbt_info_schema import parse_info_schema
from artifact_parser.dbt_info_schema.base import decode_json_column
from artifact_parser.dbt_info_schema.plugin import DbtInfoSchemaParser


def test_load_skips_internal_tables(info_schema_dir) -> None:
    tables = load_info_schema(info_schema_dir)
    assert "dbt.models" in tables
    assert "dbt_rt.run_results" in tables
    assert not any(name.startswith("dbt_internal.") for name in tables)


def test_parse_both_samples(info_schema_dir) -> None:
    info = parse_info_schema(info_schema_dir)
    assert isinstance(info, InfoSchemaV1)
    assert info.dbt_project[0].schema_version == 1
    assert info.dbt_models
    assert info.dbt_rt_run_results


def test_json_columns_are_decoded(info_schema_dir) -> None:
    info = parse_info_schema(info_schema_dir)
    assert isinstance(info.dbt_models[0].config, dict)
    assert isinstance(info.dbt_models[0].meta, dict)
    assert isinstance(info.dbt_data_tests[0].arguments, dict)
    assert isinstance(info.dbt_macros[0].meta, dict)
    assert isinstance(info.dbt_rt_run_results[0].timing, list)
    assert isinstance(info.dbt_unit_tests[0].given, list)


def test_fusion_sample_has_column_lineage() -> None:
    info = parse_info_schema(
        Path(__file__).parents[2] / "data" / "info_schema_v1_fusion"
    )
    assert info.dbt_column_lineage


def test_registry_dispatch(info_schema_tables) -> None:
    assert "dbt_info_schema" in registry.names()
    assert isinstance(parse(info_schema_tables), InfoSchemaV1)


def test_missing_tables_are_empty_lists(info_schema_tables) -> None:
    info = parse(info_schema_tables)
    assert info.dbt_models == []
    assert info.dbt_rt_run_results == []


def test_unknown_columns_ignored_and_missing_default_none() -> None:
    info = InfoSchemaV1.model_validate(
        {"dbt.models": [{"unique_id": "model.p.m", "brand_new_column": 1}]}
    )
    assert info.dbt_models[0].unique_id == "model.p.m"
    assert info.dbt_models[0].description is None


def test_populate_by_field_name() -> None:
    assert InfoSchemaV1(dbt_models=[{"unique_id": "x"}]).dbt_models[0].unique_id == "x"


def test_unknown_schema_version_rejected() -> None:
    artifact = {"dbt.project": [{"schema_version": 99}]}
    assert not DbtInfoSchemaParser().can_parse(artifact)
    with pytest.raises(UnknownArtifactError):
        DbtInfoSchemaParser().parse(artifact)


@pytest.mark.parametrize(
    "artifact",
    [
        {},
        {"dbt.project": []},
        {"dbt.project": 3},
        {"dbt.project": [1]},
        {"dbt.project": [{"project_name": "p"}]},
        {"dbt.project": [{"schema_version": []}]},
    ],
)
def test_not_an_info_schema(artifact) -> None:
    assert not DbtInfoSchemaParser().can_parse(artifact)
    with pytest.raises(UnknownArtifactError):
        DbtInfoSchemaParser().parse(artifact)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('{"a": 1}', {"a": 1}),
        ('"{\\"a\\": 1}"', {"a": 1}),
        ("not json", "not json"),
        (None, None),
        ({"a": 1}, {"a": 1}),
        ("null", None),
    ],
)
def test_decode_json_column(raw, expected) -> None:
    assert decode_json_column(raw) == expected


def test_non_dict_row_passes_validator_to_pydantic() -> None:
    with pytest.raises(ValueError):
        InfoSchemaV1.model_validate(["not", "a", "dict"])


def test_loader_without_pyarrow(monkeypatch, info_schema_dir) -> None:
    monkeypatch.setattr(loader, "pq", None)
    with pytest.raises(OptionalDependencyError, match="info-schema"):
        load_info_schema(info_schema_dir)
