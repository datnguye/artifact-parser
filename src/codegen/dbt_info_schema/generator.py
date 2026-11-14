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

PACKAGE_DIR = Path(artifact_parser.__file__).resolve().parent
INFO_SCHEMA_DIR = PACKAGE_DIR / "dbt_info_schema"
SNAPSHOT_PATH = INFO_SCHEMA_DIR / "resources" / "info_schema_v1.json"
MODEL_PATH = INFO_SCHEMA_DIR / "generated" / "models" / "info_schema_v1.py"

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
        table = path.name.removesuffix(".parquet")
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


def write_snapshot(info_schema_dir: Path) -> None:
    """Rewrite the committed schema snapshot from a real info-schema directory."""
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
