"""dbt 2.0 parquet "information schema" parser.

dbt writes ``target/info_schema/v1/<schema>.<table>.parquet`` when run with
``--generate-info-schema``. :func:`load_info_schema` reads the public tables
(``dbt.*`` and ``dbt_rt.*``) into ``{"dbt.models": [row, ...], ...}`` and
:func:`parse_info_schema` types them as :class:`InfoSchemaV1`. The loader needs
the optional ``info-schema`` extra (``pyarrow``); the rest does not.

Importing this package registers :class:`DbtInfoSchemaParser` with the shared
registry, so ``registry.parse(tables)`` dispatches on ``dbt.project``.
"""

from artifact_parser.core.registry import registry
from artifact_parser.dbt_info_schema.generated.models.info_schema_v1 import InfoSchemaV1
from artifact_parser.dbt_info_schema.loader import load_info_schema
from artifact_parser.dbt_info_schema.loader import parse_info_schema
from artifact_parser.dbt_info_schema.plugin import DbtInfoSchemaParser

dbt_info_schema_parser = DbtInfoSchemaParser()
registry.register(dbt_info_schema_parser)

__all__ = [
    "DbtInfoSchemaParser",
    "InfoSchemaV1",
    "dbt_info_schema_parser",
    "load_info_schema",
    "parse_info_schema",
]
