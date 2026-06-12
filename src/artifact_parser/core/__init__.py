"""Core parser framework: base model, plugin protocol, and the registry."""

from artifact_parser.core.base import BaseArtifactModel
from artifact_parser.core.exceptions import ArtifactParserError
from artifact_parser.core.exceptions import ParserRegistrationError
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.core.parser import ArtifactParser
from artifact_parser.core.registry import ParserRegistry
from artifact_parser.core.registry import registry

__all__ = [
    "ArtifactParser",
    "ArtifactParserError",
    "BaseArtifactModel",
    "ParserRegistrationError",
    "ParserRegistry",
    "UnknownArtifactError",
    "registry",
]
