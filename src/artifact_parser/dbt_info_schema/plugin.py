"""The dbt info-schema plugin: glues the parquet models into the registry."""

from artifact_parser.core.base import BaseArtifactModel
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.core.parser import ArtifactParser
from artifact_parser.dbt_info_schema.utils import get_info_schema_version
from artifact_parser.dbt_info_schema.utils import get_model_class


class DbtInfoSchemaParser(ArtifactParser):
    """Parses a ``{"dbt.project": [...], "dbt.models": [...], ...}`` table dict."""

    name = "dbt_info_schema"

    def can_parse(self, artifact: dict) -> bool:
        """Return ``True`` if ``artifact`` has a ``dbt.project`` of a known version."""
        try:
            get_model_class(get_info_schema_version(artifact))
        except UnknownArtifactError:
            return False
        return True

    def parse(self, artifact: dict) -> BaseArtifactModel:
        """Parse the table dict into its versioned model.

        Raises:
            UnknownArtifactError: if the schema version is missing or unknown.
        """
        model_class = get_model_class(get_info_schema_version(artifact))
        return model_class.model_validate(artifact)
