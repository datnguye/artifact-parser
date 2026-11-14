"""Tests for the info-schema codegen (snapshot + model generation)."""

import json
from unittest import mock

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.dbt_info_schema import base
from artifact_parser.dbt_info_schema import loader
from codegen.dbt_info_schema import generator


def test_constants_match_runtime() -> None:
    assert generator.JSON_EXTRA_KEY == base.JSON_EXTRA_KEY
    assert generator.PUBLIC_PREFIXES == loader.PUBLIC_PREFIXES


def test_class_name() -> None:
    assert generator.class_name("dbt_rt.run_results") == "DbtRtRunResults"


@pytest.mark.parametrize(
    ("column", "arrow_type", "expected"),
    [
        ("config", pa.string(), {"x-json": True}),
        ("a", pa.bool_(), {"type": "boolean"}),
        ("a", pa.int64(), {"type": "integer"}),
        ("a", pa.float64(), {"type": "number"}),
        ("a", pa.timestamp("us", tz="UTC"), {"type": "string", "format": "date-time"}),
        ("a", pa.string(), {"type": "string"}),
        ("a", pa.list_(pa.string()), {"type": "array", "items": {"type": "string"}}),
    ],
)
def test_column_schema(column, arrow_type, expected) -> None:
    assert generator.column_schema(column, arrow_type) == expected


def test_committed_snapshot_is_reproducible(info_schema_dir) -> None:
    committed = json.loads(generator.SNAPSHOT_PATH.read_text())
    assert generator.build_snapshot(info_schema_dir) == committed
    assert not any(name.startswith("DbtInternal") for name in committed["definitions"])


def test_write_snapshot(tmp_path, monkeypatch, info_schema_dir) -> None:
    target = tmp_path / "out" / "snap.json"
    monkeypatch.setattr(generator, "SNAPSHOT_PATH", target)
    generator.write_snapshot(info_schema_dir)
    assert json.loads(target.read_text())["title"] == "InfoSchemaV1"


def test_generate_model_runs_datamodel_codegen(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(generator, "MODEL_PATH", tmp_path / "m" / "model.py")
    with mock.patch("codegen.dbt_info_schema.generator.subprocess.run") as run:
        generator.generate_model()
    assert run.call_args.args[0][0] == "datamodel-codegen"
    assert (tmp_path / "m").is_dir()


def test_build_snapshot_skips_internal_tables(tmp_path) -> None:
    pq.write_table(pa.table({"a": ["x"]}), tmp_path / "dbt_internal.t.parquet")
    pq.write_table(pa.table({"a": ["x"]}), tmp_path / "dbt.t.parquet")
    assert list(generator.build_snapshot(tmp_path)["definitions"]) == ["DbtT"]


def test_snapshot_version_reads_project_table(info_schema_dir) -> None:
    assert generator.snapshot_version(info_schema_dir) == generator.SNAPSHOT_VERSION


@pytest.mark.parametrize("version", [None, 2])
def test_write_snapshot_refuses_non_snapshot_dirs(
    tmp_path, monkeypatch, version
) -> None:
    target = tmp_path / "snap.json"
    monkeypatch.setattr(generator, "SNAPSHOT_PATH", target)
    if version is not None:
        pq.write_table(
            pa.table({"schema_version": [version]}), tmp_path / generator.PROJECT_FILE
        )
    with pytest.raises(UnknownArtifactError):
        generator.write_snapshot(tmp_path)
    assert not target.exists()
