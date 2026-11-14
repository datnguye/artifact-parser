"""Shared fixtures for the test suite (DRY — no per-test artifact literals)."""

from pathlib import Path

import pytest

CATALOG_V1_URL = "https://schemas.getdbt.com/dbt/catalog/v1.json"
MANIFEST_V12_URL = "https://schemas.getdbt.com/dbt/manifest/v12.json"
SOURCES_V3_URL = "https://schemas.getdbt.com/dbt/sources/v3.json"
RUN_RESULTS_V6_URL = "https://schemas.getdbt.com/dbt/run-results/v6.json"


def _artifact(schema_url: str, **extra: object) -> dict:
    """Build a minimal dbt artifact dict with the given schema version."""
    return {"metadata": {"dbt_schema_version": schema_url}, **extra}


@pytest.fixture
def catalog_v1() -> dict:
    """A minimal but valid ``catalog.json`` v1 artifact."""
    return _artifact(CATALOG_V1_URL, nodes={}, sources={})


@pytest.fixture
def manifest_v12() -> dict:
    """A minimal but valid ``manifest.json`` v12 artifact."""
    return _artifact(
        MANIFEST_V12_URL,
        nodes={},
        sources={},
        macros={},
        docs={},
        exposures={},
        metrics={},
        groups={},
        selectors={},
        disabled={},
        parent_map={},
        child_map={},
        group_map={},
        saved_queries={},
        semantic_models={},
        unit_tests={},
    )


@pytest.fixture
def sources_v3() -> dict:
    """A minimal but valid ``sources.json`` v3 artifact."""
    return _artifact(SOURCES_V3_URL, results=[], elapsed_time=0.0)


@pytest.fixture
def run_results_v6() -> dict:
    """A minimal but valid ``run-results.json`` v6 artifact."""
    return _artifact(RUN_RESULTS_V6_URL, results=[], elapsed_time=0.0, args={})


INFO_SCHEMA_SAMPLES = ("info_schema_v1_fusion", "info_schema_v1_oss")


@pytest.fixture(params=INFO_SCHEMA_SAMPLES)
def info_schema_dir(request: pytest.FixtureRequest) -> Path:
    """Each real dbt 2.0 ``info_schema/v1`` sample directory (Fusion, OSS)."""
    return Path(__file__).parent / "data" / request.param


@pytest.fixture
def info_schema_tables() -> dict:
    """A minimal valid table dict for the info-schema plugin."""
    return {"dbt.project": [{"schema_version": 1, "project_name": "p"}]}
