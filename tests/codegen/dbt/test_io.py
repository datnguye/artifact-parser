"""Tests for codegen's side-effecting steps (download / generate / write)."""

from pathlib import Path
from unittest import mock

from codegen.dbt import generator
from codegen.dbt.artifact_spec import ARTIFACT_SPECS
from codegen.dbt.artifact_spec import get_spec

MANIFEST = get_spec("manifest")


def test_download_schema_writes_bytes(tmp_path: Path) -> None:
    response = mock.MagicMock()
    response.read.return_value = b'{"ok": true}'
    response.__enter__.return_value = response
    dest = tmp_path / "manifest" / "manifest_v12.json"
    with (
        mock.patch.object(generator.urllib.request, "urlopen", return_value=response),
        mock.patch.object(generator, "resource_path", return_value=dest),
    ):
        generator.download_schema(MANIFEST, "v12")
    assert dest.read_bytes() == b'{"ok": true}'


def test_schema_exists_true() -> None:
    with mock.patch.object(generator.urllib.request, "urlopen"):
        assert generator.schema_exists(MANIFEST, "v12") is True


def test_schema_exists_false_on_404() -> None:
    err = generator.urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    with mock.patch.object(generator.urllib.request, "urlopen", side_effect=err):
        assert generator.schema_exists(MANIFEST, "v99") is False


def test_discover_versions_stops_after_gap() -> None:
    # v1, v2 exist; v3, v4, v5 miss -> discovery stops, returns (v1, v2).
    present = {"v1", "v2"}
    with mock.patch.object(
        generator, "schema_exists", side_effect=lambda spec, v: v in present
    ):
        assert generator.discover_versions(MANIFEST) == ("v1", "v2")


def test_discover_all_covers_every_family() -> None:
    with mock.patch.object(generator, "discover_versions", return_value=("v1",)):
        table = generator.discover_all()
    assert set(table) == {spec.name for spec in ARTIFACT_SPECS}
    assert all(v == ("v1",) for v in table.values())


def test_write_versions_roundtrips(tmp_path: Path) -> None:
    target = tmp_path / "versions.py"
    table = {"manifest": ("v1", "v2"), "catalog": ("v1",)}
    with mock.patch.object(generator.paths, "VERSIONS_PATH", target):
        generator.write_versions(table)
    namespace: dict = {}
    exec(compile(target.read_text(), "versions.py", "exec"), namespace)
    assert namespace["VERSIONS"] == table


def test_reload_specs_returns_fresh_specs() -> None:
    specs = generator.reload_specs()
    assert {spec.name for spec in specs} == {
        "catalog",
        "manifest",
        "run-results",
        "sources",
    }


def test_generate_model_invokes_datamodel_codegen(tmp_path: Path) -> None:
    src = tmp_path / "manifest_v12.json"
    out = tmp_path / "models" / "manifest_v12.py"
    out.parent.mkdir(parents=True, exist_ok=True)
    # datamodel-codegen would write the model; stub it so the post-gen relax step
    # has a file to read.
    out.write_text("model_config = ConfigDict(extra='forbid')\n")
    with (
        mock.patch.object(generator, "resource_path", return_value=src),
        mock.patch.object(generator, "model_path", return_value=out),
        mock.patch.object(generator.subprocess, "run") as run,
    ):
        generator.generate_model(MANIFEST, "v12")
    cmd = run.call_args.args[0]
    assert cmd[0] == "datamodel-codegen"
    assert "--class-name" in cmd
    assert cmd[cmd.index("--class-name") + 1] == "ManifestV12"
    # The forbidding policy is relaxed in place after generation.
    assert "extra='ignore'" in out.read_text()


def test_relax_extra_policy_rewrites_forbid(tmp_path: Path) -> None:
    model = tmp_path / "model.py"
    model.write_text("    model_config = ConfigDict(extra='forbid')\n")
    generator.relax_extra_policy(model)
    assert model.read_text() == "    model_config = ConfigDict(extra='ignore')\n"


def test_relax_extra_policy_noop_without_forbid(tmp_path: Path) -> None:
    model = tmp_path / "model.py"
    original = "    model_config = ConfigDict(extra='allow')\n"
    model.write_text(original)
    generator.relax_extra_policy(model)
    assert model.read_text() == original


def test_ensure_models_packages_creates_inits(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    dest = models_dir / "manifest" / "manifest_v12.py"
    with mock.patch.object(generator.paths, "MODELS_DIR", models_dir):
        generator._ensure_models_packages(dest)
    assert (models_dir / "__init__.py").exists()
    assert (models_dir / "manifest" / "__init__.py").exists()


def test_ensure_models_packages_idempotent(tmp_path: Path) -> None:
    models_dir = tmp_path / "models"
    dest = models_dir / "manifest" / "manifest_v12.py"
    with mock.patch.object(generator.paths, "MODELS_DIR", models_dir):
        generator._ensure_models_packages(dest)
        sentinel = models_dir / "__init__.py"
        sentinel.write_text("# kept")
        generator._ensure_models_packages(dest)
    assert sentinel.read_text() == "# kept"


def test_write_generated_init(tmp_path: Path) -> None:
    target = tmp_path / "generated" / "__init__.py"
    with mock.patch.object(generator.paths, "GENERATED_INIT_PATH", target):
        generator.write_generated_init()
    assert "DO NOT EDIT" in target.read_text()


def test_write_version_map(tmp_path: Path) -> None:
    target = tmp_path / "version_map.py"
    with mock.patch.object(generator.paths, "VERSION_MAP_PATH", target):
        generator.write_version_map(ARTIFACT_SPECS)
    compile(target.read_text(), "version_map.py", "exec")


def test_write_parser(tmp_path: Path) -> None:
    target = tmp_path / "parser.py"
    with mock.patch.object(generator.paths, "PARSER_PATH", target):
        generator.write_parser(ARTIFACT_SPECS)
    compile(target.read_text(), "parser.py", "exec")
