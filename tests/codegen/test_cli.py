"""Tests for the ``codegen`` typer CLI."""

from unittest import mock

import pytest
from typer.testing import CliRunner

from codegen import cli
from codegen.cli import app
from codegen.dbt.artifact_spec import ARTIFACT_SPECS

runner = CliRunner()


@pytest.fixture
def patched_generator():
    """Stub every side-effecting generator call so the CLI runs offline."""
    with (
        mock.patch("codegen.cli.generator.download_schema") as download,
        mock.patch("codegen.cli.generator.generate_model") as generate,
        mock.patch("codegen.cli.generator.write_generated_init") as write_init,
        mock.patch("codegen.cli.generator.write_version_map") as write_map,
        mock.patch("codegen.cli.generator.write_parser") as write_parser,
        mock.patch(
            "codegen.cli.generator.discover_all",
            return_value={
                "catalog": ("v1",),
                "manifest": ("v1",),
                "run-results": ("v1",),
                "sources": ("v1",),
            },
        ) as discover,
        mock.patch("codegen.cli.generator.write_versions") as write_versions,
        mock.patch(
            "codegen.cli.generator.reload_specs", return_value=ARTIFACT_SPECS
        ) as reload_specs,
    ):
        yield {
            "download": download,
            "generate": generate,
            "write_init": write_init,
            "write_map": write_map,
            "write_parser": write_parser,
            "discover": discover,
            "write_versions": write_versions,
            "reload_specs": reload_specs,
        }


def test_dbt_all(patched_generator: dict) -> None:
    result = runner.invoke(app, ["dbt"])
    assert result.exit_code == 0
    assert patched_generator["download"].called
    assert patched_generator["generate"].called
    assert patched_generator["write_map"].call_count == 1
    assert patched_generator["write_parser"].call_count == 1


def test_dbt_single_type_and_version(patched_generator: dict) -> None:
    result = runner.invoke(app, ["dbt", "manifest", "v12"])
    assert result.exit_code == 0
    assert patched_generator["generate"].call_count == 1


def test_dbt_skip_download(patched_generator: dict) -> None:
    result = runner.invoke(app, ["dbt", "catalog", "--skip-download"])
    assert result.exit_code == 0
    assert not patched_generator["download"].called
    assert patched_generator["generate"].called


def test_dbt_unknown_type_exits_2(patched_generator: dict) -> None:
    result = runner.invoke(app, ["dbt", "nope"])
    assert result.exit_code == 2
    assert "Unknown artifact type" in result.output
    assert not patched_generator["generate"].called


def test_dbt_discover_refreshes_versions_and_generates(
    patched_generator: dict,
) -> None:
    result = runner.invoke(app, ["dbt", "--discover"])
    assert result.exit_code == 0
    assert patched_generator["discover"].call_count == 1
    assert patched_generator["write_versions"].call_count == 1
    assert patched_generator["reload_specs"].call_count == 1
    assert patched_generator["generate"].called
    assert "probing schemas.getdbt.com" in result.output


def test_dbt_discover_with_skip_download_exits_2(patched_generator: dict) -> None:
    result = runner.invoke(app, ["dbt", "--discover", "--skip-download"])
    assert result.exit_code == 2
    assert "cannot be combined" in result.output
    assert not patched_generator["discover"].called
    assert not patched_generator["generate"].called


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code != 0  # no_args_is_help exits non-zero
    assert "Usage" in result.output


def test_main_invokes_app() -> None:
    with mock.patch.object(cli, "app") as app_mock:
        cli.main()
    app_mock.assert_called_once_with()
