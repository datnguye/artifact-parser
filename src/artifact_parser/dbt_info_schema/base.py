"""Base class for every generated info-schema row model and the container."""

import json
from typing import Any

from pydantic import ConfigDict
from pydantic import model_validator

from artifact_parser.core.base import BaseArtifactModel

JSON_EXTRA_KEY = "x-json"


def decode_json_column(value: Any) -> Any:
    """Decode a JSON-encoded VARCHAR value, tolerating double encoding.

    dbt sometimes JSON-encodes an already JSON-encoded object (``"\\"{...}\\""``),
    so decoding repeats while the result is still a JSON string. Values that are
    not valid JSON are returned untouched rather than rejected.
    """
    while isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


class InfoSchemaModel(BaseArtifactModel):
    """Root of the info-schema models.

    Unknown columns are ignored (forward drift). Fields flagged ``x-json`` in the
    committed schema snapshot hold JSON text in the parquet file and are decoded
    into dicts/lists on validation.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def _decode_json_columns(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        decoded = dict(data)
        for name, field in cls.model_fields.items():
            extra = field.json_schema_extra
            if isinstance(extra, dict) and extra.get(JSON_EXTRA_KEY):
                key = field.alias or name
                if key in decoded:
                    decoded[key] = decode_json_column(decoded[key])
        return decoded
