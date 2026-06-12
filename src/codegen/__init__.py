"""codegen — regenerate the dbt models from dbt-core's published JSON schemas.

A developer CLI, shipped as its own package so it can carry the
``datamodel-code-generator`` dependency without bloating the runtime library.
The console entry point is ``codegen`` (see :func:`codegen.cli.main`).
"""

from codegen.cli import main

__all__ = ["main"]
