"""The ``codegen`` command line (typer): parse args, drive the generator, report.

Per ``(artifact, version)`` selected it downloads the dbt-core schema, generates
a pydantic model from it, and finally rewrites ``version_map.py`` so the
schema-URL → model-class table always matches what's on disk.
"""

from pathlib import Path

import typer

from codegen.dbt import generator
from codegen.dbt.artifact_spec import ARTIFACT_SPECS
from codegen.dbt.artifact_spec import ArtifactSpec
from codegen.dbt_info_schema import generator as info_schema_generator

app = typer.Typer(
    name="codegen",
    help="Generate artifact-parser models from upstream JSON schemas.",
    add_completion=False,
    no_args_is_help=True,
)


@app.callback()
def _root() -> None:
    """Group the per-plugin codegen subcommands (``codegen dbt`` today)."""


@app.command()
def dbt(
    artifact_type: str | None = typer.Argument(
        None,
        help="One of: catalog, manifest, run-results, sources. Omit for all.",
    ),
    versions: list[str] | None = typer.Argument(
        None,
        help="Versions to generate (e.g. v1 v12). Omit for all of the type.",
    ),
    skip_download: bool = typer.Option(
        False,
        "--skip-download",
        help="Reuse cached schemas in resources/ instead of re-downloading.",
    ),
    discover: bool = typer.Option(
        False,
        "--discover",
        help="Probe schemas.getdbt.com for every published version, refresh the "
        "versions table, and generate all of them. Implies a fresh download.",
    ),
) -> None:
    """Generate the dbt artifact models from dbt's published JSON schemas."""
    specs: tuple[ArtifactSpec, ...] = ARTIFACT_SPECS
    if discover:
        if skip_download:
            typer.secho(
                "error: --discover probes the network and cannot be combined "
                "with --skip-download.",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(code=2)
        typer.echo("discover: probing schemas.getdbt.com for published versions")
        table = generator.discover_all()
        for name, found in table.items():
            typer.echo(f"  {name}: {', '.join(found) or '(none)'}")
        generator.write_versions(table)
        specs = generator.reload_specs()

    try:
        targets = generator.resolve_targets(artifact_type, versions or [], specs)
    except (KeyError, ValueError) as exc:
        typer.secho(f"error: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=2) from exc

    for spec, version in targets:
        typer.echo(f"{spec.name} {version}:")
        if not skip_download:
            typer.echo(f"  download <- {generator.schema_url(spec, version)}")
            generator.download_schema(spec, version)
        typer.echo(f"  generate -> {generator.model_path(spec, version).name}")
        generator.generate_model(spec, version)

    typer.echo("generated: writing __init__.py + version_map.py + parser.py")
    generator.write_generated_init()
    generator.write_version_map(specs)
    generator.write_parser(specs)
    typer.secho(
        "Done. Run `task format` to normalise the generated code.",
        fg=typer.colors.GREEN,
    )


@app.command(name="dbt-info-schema")
def dbt_info_schema(
    snapshot_from: Path | None = typer.Option(
        None,
        "--snapshot-from",
        help="A real `target/info_schema/v1` dir to re-derive the committed schema "
        "snapshot from. Omit to regenerate the models from the committed snapshot.",
    ),
) -> None:
    """Generate the dbt info-schema (parquet) models from the schema snapshot."""
    if snapshot_from is not None:
        typer.echo(f"snapshot <- {snapshot_from}")
        info_schema_generator.write_snapshot(snapshot_from)
    typer.echo(f"generate -> {info_schema_generator.MODEL_PATH.name}")
    info_schema_generator.generate_model()
    typer.secho(
        "Done. Run `task format` to normalise the generated code.",
        fg=typer.colors.GREEN,
    )


def main() -> None:
    """Entry point for the ``codegen`` console script."""
    app()
