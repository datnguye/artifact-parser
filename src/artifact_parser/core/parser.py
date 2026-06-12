"""The :class:`ArtifactParser` protocol every plugin implements."""

from abc import ABC
from abc import abstractmethod

from artifact_parser.core.base import BaseArtifactModel


class ArtifactParser(ABC):
    """Contract for a parser plugin (e.g. the dbt-core artifacts plugin).

    A plugin owns one *family* of artifacts. It answers two questions: "is this
    blob mine?" (:meth:`can_parse`) and "turn it into a typed model"
    (:meth:`parse`). The :data:`~artifact_parser.core.registry.registry`
    dispatches to the first plugin that claims the blob, so plugins should keep
    :meth:`can_parse` cheap and specific.
    """

    #: Stable, unique identifier for the plugin (e.g. ``"dbt"``).
    name: str

    @abstractmethod
    def can_parse(self, artifact: dict) -> bool:
        """Return ``True`` if this plugin recognises ``artifact``."""

    @abstractmethod
    def parse(self, artifact: dict) -> BaseArtifactModel:
        """Parse ``artifact`` into a typed model, or raise on a mismatch."""
