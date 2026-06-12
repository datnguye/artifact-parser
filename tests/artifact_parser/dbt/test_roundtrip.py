"""Round-trip tests against real dbt artifacts produced by a live project.

The fixtures in ``conftest.py`` carry empty collections, which exercise dispatch
but not deserialization of populated rows. These tests load real artifacts from
``tests/data/`` (a ``dbt build`` of the jaffle_shop project on Snowflake) through
the public :func:`parse` entry point and assert the nested, typed structure
survives — the kind of regression a codegen change could introduce that the
minimal fixtures would sail straight past.

The manifest here is the load-bearing case: real dbt manifests are a *superset*
of the published v12 JSON schema (macros carry a ``config`` block the schema
omits), so this only parses because codegen relaxes the generated models to
``extra="ignore"`` — see ``codegen.dbt.generator.relax_extra_policy``.
"""

import json
from pathlib import Path

import pytest

from artifact_parser import parse
from artifact_parser.dbt.generated.models.catalog.catalog_v1 import CatalogV1
from artifact_parser.dbt.generated.models.manifest.manifest_v12 import ManifestV12
from artifact_parser.dbt.generated.models.run_results.run_results_v6 import RunResultsV6

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def _load(name: str) -> dict:
    """Load a real artifact JSON file from ``tests/data/``."""
    return json.loads((DATA_DIR / name).read_text())


@pytest.fixture
def catalog_v1_real() -> dict:
    """A real ``catalog.json`` (v1) from a jaffle_shop build."""
    return _load("catalog_v1.json")


@pytest.fixture
def manifest_v12_real() -> dict:
    """A real ``manifest.json`` (v12) from a jaffle_shop build."""
    return _load("manifest_v12.json")


@pytest.fixture
def run_results_v6_real() -> dict:
    """A real ``run_results.json`` (v6) from a jaffle_shop build."""
    return _load("run-results_v6.json")


def test_catalog_roundtrip(catalog_v1_real: dict) -> None:
    model = parse(catalog_v1_real)
    assert isinstance(model, CatalogV1)
    node = model.nodes["model.jaffle_shop.stg_products"]
    assert node.metadata.schema_ == "JF"
    assert node.columns["PRODUCT_ID"].type == "TEXT"
    assert node.stats["has_stats"].include is False


def test_manifest_roundtrip(manifest_v12_real: dict) -> None:
    # Only parses because generated models use extra="ignore": real manifests
    # carry fields the published v12 schema does not describe.
    model = parse(manifest_v12_real)
    assert isinstance(model, ManifestV12)
    assert len(model.nodes) == 50
    node = model.nodes["model.jaffle_shop.stg_products"]
    assert node.resource_type == "model"
    assert node.package_name == "jaffle_shop"


def test_run_results_roundtrip(run_results_v6_real: dict) -> None:
    model = parse(run_results_v6_real)
    assert isinstance(model, RunResultsV6)
    assert len(model.results) == 50
    result = model.results[0]
    assert result.unique_id == "model.jaffle_shop.stg_order_items"
    assert result.status.value == "success"
    assert [t.name for t in result.timing] == ["compile", "execute"]
