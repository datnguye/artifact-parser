"""Snapshot the info-schema parquet columns and generate the pydantic models.

The parquet column schema *is* dbt's contract (there is no published JSON
Schema), so :func:`build_snapshot` derives a JSON Schema from a real
``info_schema/v1`` directory and commits it; :func:`generate_model` then runs
``datamodel-codegen`` over that snapshot, exactly like the dbt models.
"""

import json
import subprocess
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import artifact_parser
from artifact_parser.core.exceptions import UnknownArtifactError

PACKAGE_DIR = Path(artifact_parser.__file__).resolve().parent
INFO_SCHEMA_DIR = PACKAGE_DIR / "dbt_info_schema"
SNAPSHOT_VERSION = 1
SNAPSHOT_PATH = INFO_SCHEMA_DIR / "resources" / f"info_schema_v{SNAPSHOT_VERSION}.json"
MODEL_PATH = (
    INFO_SCHEMA_DIR / "generated" / "models" / f"info_schema_v{SNAPSHOT_VERSION}.py"
)
PROJECT_FILE = "dbt.project.parquet"

JSON_EXTRA_KEY = "x-json"
PUBLIC_PREFIXES = ("dbt.", "dbt_rt.")

ROOT_CLASS = "InfoSchemaV1"
BASE_CLASS = "artifact_parser.dbt_info_schema.base.InfoSchemaModel"
TARGET_PYTHON = "3.10"
OUTPUT_MODEL_TYPE = "pydantic_v2.BaseModel"

JSON_COLUMNS = frozenset(
    {
        "adapter_response",
        "agg_params",
        "args",
        "arguments",
        "batch_results",
        "config",
        "constraints",
        "custom_granularities",
        "defaults",
        "exports",
        "expect",
        "external",
        "freshness",
        "given",
        "grants",
        "meta",
        "metric_filter",
        "node_relation",
        "non_additive_dimension",
        "overrides",
        "persist_docs",
        "post_hook",
        "pre_hook",
        "query_params",
        "quoting",
        "source_meta",
        "tests",
        "timing",
        "type_params",
        "validity_params",
        "vars_override",
        "versions",
    }
)


def class_name(table: str) -> str:
    """Return the row model name for a table, e.g. ``dbt.models`` -> ``DbtModels``."""
    return "".join(part.capitalize() for part in table.replace(".", "_").split("_"))


def column_schema(column: str, arrow_type: pa.DataType) -> dict:
    """Map one parquet column to its JSON Schema property."""
    if column in JSON_COLUMNS:
        return {JSON_EXTRA_KEY: True}
    if pa.types.is_boolean(arrow_type):
        return {"type": "boolean"}
    if pa.types.is_integer(arrow_type):
        return {"type": "integer"}
    if pa.types.is_floating(arrow_type):
        return {"type": "number"}
    if pa.types.is_timestamp(arrow_type):
        return {"type": "string", "format": "date-time"}
    if pa.types.is_list(arrow_type):
        return {"type": "array", "items": column_schema("", arrow_type.value_type)}
    return {"type": "string"}


def build_snapshot(info_schema_dir: Path) -> dict:
    """Derive the JSON Schema for every public table under ``info_schema_dir``."""
    definitions: dict[str, dict] = {}
    properties: dict[str, dict] = {}
    for path in sorted(info_schema_dir.glob("*.parquet")):
        table = path.stem
        if not table.startswith(PUBLIC_PREFIXES):
            continue
        schema = pq.read_schema(path)
        definitions[class_name(table)] = {
            "type": "object",
            "properties": {
                name: column_schema(name, schema.field(name).type)
                for name in schema.names
            },
        }
        properties[table] = {
            "type": "array",
            "items": {"$ref": f"#/definitions/{class_name(table)}"},
            "default": [],
        }
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": ROOT_CLASS,
        "type": "object",
        "properties": properties,
        "definitions": definitions,
    }


def snapshot_version(info_schema_dir: Path) -> int:
    """Return ``dbt.project.schema_version`` of a real info-schema directory.

    Raises:
        UnknownArtifactError: if the directory has no ``dbt.project`` table — so
            an empty or failed dbt run can never be snapshotted as "every table
            was removed".
    """
    project = info_schema_dir / PROJECT_FILE
    if not project.is_file():
        raise UnknownArtifactError(
            f"{info_schema_dir} has no {PROJECT_FILE}; "
            "run dbt with --generate-info-schema."
        )
    rows = pq.read_table(project, columns=["schema_version"]).to_pylist()
    return rows[0]["schema_version"]


def write_snapshot(info_schema_dir: Path) -> None:
    """Rewrite the committed schema snapshot from a real info-schema directory.

    Raises:
        UnknownArtifactError: if the directory is not an info schema, or its
            ``schema_version`` is not :data:`SNAPSHOT_VERSION` — a new parquet
            layout needs a new snapshot, model module and ``VERSION_MODELS`` row,
            not an in-place overwrite of the current one.
    """
    version = snapshot_version(info_schema_dir)
    if version != SNAPSHOT_VERSION:
        raise UnknownArtifactError(
            f"info schema version {version!r} is not the snapshotted "
            f"v{SNAPSHOT_VERSION}; add a new layout instead of overwriting."
        )
    SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
    snapshot = build_snapshot(info_schema_dir)
    SNAPSHOT_PATH.write_text(json.dumps(snapshot, indent=2) + "\n")


def generate_model() -> None:
    """Run ``datamodel-codegen`` over the committed snapshot."""
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "datamodel-codegen",
            "--input-file-type",
            "jsonschema",
            "--target-python-version",
            TARGET_PYTHON,
            "--output-model-type",
            OUTPUT_MODEL_TYPE,
            "--disable-timestamp",
            "--formatters",
            "black",
            "isort",
            "--base-class",
            BASE_CLASS,
            "--strict-nullable",
            "--field-extra-keys",
            JSON_EXTRA_KEY,
            "--class-name",
            ROOT_CLASS,
            "--input",
            str(SNAPSHOT_PATH),
            "--output",
            str(MODEL_PATH),
        ],
        check=True,
    )
