"""A small registry that routes an artifact to the plugin that owns it."""

from artifact_parser.core.base import BaseArtifactModel
from artifact_parser.core.exceptions import ParserRegistrationError
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.core.parser import ArtifactParser


class ParserRegistry:
    """Holds the known parser plugins and dispatches artifacts to them.

    Registration order is preserved, so :meth:`parse` tries plugins in the
    order they were added and returns the first match. There is one module-level
    instance (:data:`registry`); most callers never build their own.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, ArtifactParser] = {}

    def register(self, parser: ArtifactParser) -> None:
        """Add ``parser`` to the registry, keyed by its ``name``.

        Raises:
            ParserRegistrationError: if the name is already taken.
        """
        if parser.name in self._parsers:
            raise ParserRegistrationError(
                f"A parser named {parser.name!r} is already registered."
            )
        self._parsers[parser.name] = parser

    def unregister(self, name: str) -> None:
        """Remove the parser registered under ``name``.

        Raises:
            UnknownArtifactError: if no parser is registered under ``name``.
        """
        if name not in self._parsers:
            raise UnknownArtifactError(f"No parser named {name!r} is registered.")
        del self._parsers[name]

    def get(self, name: str) -> ArtifactParser:
        """Return the parser registered under ``name``.

        Raises:
            UnknownArtifactError: if no parser is registered under ``name``.
        """
        if name not in self._parsers:
            raise UnknownArtifactError(f"No parser named {name!r} is registered.")
        return self._parsers[name]

    def names(self) -> list[str]:
        """Return the registered plugin names, in registration order."""
        return list(self._parsers)

    def parse(self, artifact: dict) -> BaseArtifactModel:
        """Parse ``artifact`` with the first plugin that claims it.

        Raises:
            UnknownArtifactError: if no registered plugin recognises it.
        """
        for parser in self._parsers.values():
            if parser.can_parse(artifact):
                return parser.parse(artifact)
        raise UnknownArtifactError(
            "No registered parser recognises this artifact. "
            f"Tried: {', '.join(self._parsers) or '(none registered)'}."
        )


#: The process-wide registry. Plugins register themselves against this.
registry = ParserRegistry()
