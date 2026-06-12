"""artifact-parser — a pluggable framework for parsing data tool artifacts.

The framework is source-agnostic: each plugin owns one family of artifacts and
registers itself with the shared :data:`~artifact_parser.core.registry.registry`.
The first (and currently only) plugin parses dbt-core artifacts.

The headline entry point is :func:`parse`, which sniffs any supported artifact
and routes it to the right plugin::

    from artifact_parser import parse
    model = parse(json.loads(manifest_path.read_text()))

For dbt-specific, version-pinned parsing, import from
:mod:`artifact_parser.dbt` directly.

The dbt plugin's generated code lives under ``artifact_parser/dbt/generated/``
and may be deleted and rebuilt with ``codegen dbt``. While it is absent the dbt
plugin simply does not register — the framework (and the codegen CLI it needs to
rebuild itself) still imports cleanly.
"""

import importlib
import warnings

from artifact_parser.core import ArtifactParser
from artifact_parser.core import ArtifactParserError
from artifact_parser.core import BaseArtifactModel
from artifact_parser.core import ParserRegistrationError
from artifact_parser.core import ParserRegistry
from artifact_parser.core import UnknownArtifactError
from artifact_parser.core import registry

try:
    importlib.import_module("artifact_parser.dbt")  # registers the dbt plugin
except ImportError:  # pragma: no cover - only when dbt/generated/ is dropped
    warnings.warn(
        "artifact_parser.dbt is unavailable (generated code missing). "
        "Run `codegen dbt` to rebuild it.",
        stacklevel=2,
    )

parse = registry.parse

__all__ = [
    "ArtifactParser",
    "ArtifactParserError",
    "BaseArtifactModel",
    "ParserRegistrationError",
    "ParserRegistry",
    "UnknownArtifactError",
    "parse",
    "registry",
]
