"""Exception types raised by the parser framework."""


class ArtifactParserError(Exception):
    """Base class for every error this package raises."""


class UnknownArtifactError(ArtifactParserError):
    """Raised when no registered parser recognises the given artifact."""


class ParserRegistrationError(ArtifactParserError):
    """Raised when a parser is registered under a name that is already taken."""


class OptionalDependencyError(ArtifactParserError):
    """Raised when a feature needs an optional extra that is not installed."""
