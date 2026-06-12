"""Tests for the codegen engine (path/name helpers + template rendering)."""

import pytest

from codegen.dbt import generator
from codegen.dbt.artifact_spec import ARTIFACT_SPECS
from codegen.dbt.artifact_spec import get_spec

CATALOG = get_spec("catalog")
MANIFEST = get_spec("manifest")
RUN_RESULTS = get_spec("run-results")


def test_get_spec_unknown_type_raises() -> None:
    with pytest.raises(KeyError, match="Unknown artifact type 'nope'"):
        get_spec("nope")


def test_schema_url() -> None:
    url = generator.schema_url(MANIFEST, "v12")
    assert url == "https://schemas.getdbt.com/dbt/manifest/v12.json"


def test_resource_path_uses_hyphenated_stem() -> None:
    # run-results caches under its dbt-core (hyphenated) filename stem.
    assert generator.resource_path(RUN_RESULTS, "v6").name == "run-results_v6.json"


def test_model_path_uses_python_stem() -> None:
    assert generator.model_path(RUN_RESULTS, "v6").name == "run_results_v6.py"


def test_model_class_name() -> None:
    assert generator.model_class_name(MANIFEST, "v12") == "ManifestV12"


def test_version_map_member() -> None:
    assert generator.version_map_member(RUN_RESULTS, "v6") == "RUN_RESULTS_V6"


def test_version_map_entries_count() -> None:
    total = sum(len(spec.versions) for spec in ARTIFACT_SPECS)
    assert len(generator.version_map_entries(ARTIFACT_SPECS)) == total


def test_render_version_map_is_valid_python() -> None:
    rendered = generator.render_version_map(ARTIFACT_SPECS)
    compile(rendered, "version_map.py", "exec")
    assert "class ArtifactTypes(Enum):" in rendered
    assert "MANIFEST_V12 = ArtifactType(" in rendered


def test_family_context_single_version_union() -> None:
    # catalog has one version -> the union is just the bare class name.
    ctx = generator.family_context(CATALOG)
    assert ctx["union"] == "CatalogV1"


def test_family_context_multi_version_union() -> None:
    ctx = generator.family_context(MANIFEST)
    assert ctx["union"].startswith("(\n    ManifestV1")
    assert "| ManifestV12" in ctx["union"]


def test_render_parser_is_valid_python() -> None:
    rendered = generator.render_parser(ARTIFACT_SPECS)
    compile(rendered, "parser.py", "exec")
    assert "def parse_manifest(" in rendered
    assert "def parse_run_results_v6(" in rendered


def test_resolve_targets_all() -> None:
    total = sum(len(spec.versions) for spec in ARTIFACT_SPECS)
    assert len(generator.resolve_targets(None, [])) == total


def test_resolve_targets_one_type() -> None:
    targets = generator.resolve_targets("manifest", [])
    assert {ver for _, ver in targets} == set(MANIFEST.versions)


def test_resolve_targets_specific_versions() -> None:
    targets = generator.resolve_targets("manifest", ["v1", "v12"])
    assert [ver for _, ver in targets] == ["v1", "v12"]


def test_resolve_targets_unknown_type() -> None:
    with pytest.raises(KeyError, match="Unknown artifact type"):
        generator.resolve_targets("nope", [])


def test_resolve_targets_unknown_version() -> None:
    with pytest.raises(ValueError, match="has no version 'v99'"):
        generator.resolve_targets("manifest", ["v99"])


def test_resolve_targets_uses_passed_specs() -> None:
    # A custom specs tuple overrides the module default.
    targets = generator.resolve_targets("catalog", [], (CATALOG,))
    assert [ver for _, ver in targets] == list(CATALOG.versions)


def test_resolve_targets_unknown_type_lists_passed_specs() -> None:
    with pytest.raises(KeyError, match="Valid types: catalog"):
        generator.resolve_targets("manifest", [], (CATALOG,))


def test_render_versions_is_valid_python() -> None:
    rendered = generator.render_versions({"manifest": ("v1", "v2"), "catalog": ("v1",)})
    namespace: dict = {}
    exec(compile(rendered, "versions.py", "exec"), namespace)
    assert namespace["VERSIONS"]["manifest"] == ("v1", "v2")
