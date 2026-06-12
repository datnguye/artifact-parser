"""The dbt-core plugin: glues the dbt parser into the framework registry."""

from artifact_parser.core.base import BaseArtifactModel
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.core.parser import ArtifactParser
from artifact_parser.dbt.utils import get_artifact_type
from artifact_parser.dbt.utils import get_dbt_schema_version


class DbtArtifactParser(ArtifactParser):
    """Parses any known dbt-core artifact (catalog/manifest/run-results/sources).

    This is the framework-facing wrapper: :meth:`can_parse` sniffs the schema
    version, and :meth:`parse` hands off to the matching vendored model. The
    version-specific helpers in :mod:`artifact_parser.dbt.parser` remain
    available for callers who already know which artifact they hold.
    """

    name = "dbt"

    def can_parse(self, artifact: dict) -> bool:
        """Return ``True`` if ``artifact`` carries a known dbt schema version."""
        try:
            get_artifact_type(get_dbt_schema_version(artifact))
        except UnknownArtifactError:
            return False
        return True

    def parse(self, artifact: dict) -> BaseArtifactModel:
        """Parse ``artifact`` into its dbt model.

        Raises:
            UnknownArtifactError: if the schema version is missing or unknown.
        """
        schema_version = get_dbt_schema_version(artifact)
        model_class = get_artifact_type(schema_version).value.model_class
        return model_class(**artifact)
