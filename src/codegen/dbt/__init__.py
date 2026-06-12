"""dbt codegen — generate :mod:`artifact_parser.dbt` models from dbt-core schemas.

This submodule mirrors the runtime layout (``artifact_parser.dbt``): it owns
everything specific to generating the dbt plugin's models. A future parser
plugin would get its own ``codegen.<tool>`` sibling.
"""
