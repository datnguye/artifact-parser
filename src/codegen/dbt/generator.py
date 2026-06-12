"""The codegen engine: download schemas, generate models, write the version map.

Pure logic, no argument parsing — :mod:`codegen.cli` drives it.
"""

import importlib
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from jinja2 import Environment
from jinja2 import FileSystemLoader

from codegen.dbt import artifact_spec as artifact_spec_module
from codegen.dbt import paths
from codegen.dbt import versions as versions_module
from codegen.dbt.artifact_spec import ARTIFACT_SPECS
from codegen.dbt.artifact_spec import ArtifactSpec

SCHEMA_URL_BASE = "https://schemas.getdbt.com/dbt"

BASE_CLASS = "artifact_parser.core.base.BaseArtifactModel"
TARGET_PYTHON = "3.10"
OUTPUT_MODEL_TYPE = "pydantic_v2.BaseModel"

# dbt's published JSON schemas set ``additionalProperties: false``, so
# datamodel-codegen emits ``extra="forbid"``. Real artifacts are a *superset* of
# the published schema (e.g. dbt 1.11 manifests carry config fields the v12
# schema omits), which would make a strict model reject them outright. We relax
# every generated model to ``extra="ignore"`` so unknown fields are dropped
# rather than raising — the parser stays forward-compatible with newer dbt point
# releases without a codegen run.
# datamodel-codegen emits single-quoted config (black later normalises quotes),
# so we match its raw output here — this runs before the format step.
_FORBID_EXTRA = "extra='forbid'"
_IGNORE_EXTRA = "extra='ignore'"

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    trim_blocks=True,
    lstrip_blocks=True,
    keep_trailing_newline=True,
)


def schema_url(spec: ArtifactSpec, version: str) -> str:
    """Return the canonical published URL for one artifact schema.

    dbt publishes its versioned artifact schemas at ``schemas.getdbt.com`` —
    the same URLs that appear in each artifact's ``dbt_schema_version`` — so the
    download source is version-pinned and never moves under us.
    """
    return f"{SCHEMA_URL_BASE}/{spec.name}/{version}.json"


def resource_path(spec: ArtifactSpec, version: str) -> Path:
    """Return the local path the schema is cached at.

    The cached schema keeps dbt-core's own filename stem (``spec.name``, which is
    hyphenated for run-results); the generated model uses the Python-safe
    ``spec.package`` stem instead.
    """
    return paths.RESOURCES_DIR / spec.name / f"{spec.name}_{version}.json"


def model_path(spec: ArtifactSpec, version: str) -> Path:
    """Return the local path the generated model is written to."""
    return paths.MODELS_DIR / spec.package / f"{spec.package}_{version}.py"


def model_class_name(spec: ArtifactSpec, version: str) -> str:
    """Return the generated model class name, e.g. ``ManifestV12``."""
    return f"{spec.class_prefix}{version.capitalize()}"


def version_map_member(spec: ArtifactSpec, version: str) -> str:
    """Return the ``ArtifactTypes`` enum member name, e.g. ``MANIFEST_V12``."""
    return f"{spec.name.upper().replace('-', '_')}_{version.upper()}"


def download_schema(spec: ArtifactSpec, version: str) -> None:
    """Download one artifact schema from dbt's published schemas into ``resources/``."""
    url = schema_url(spec, version)
    dest = resource_path(spec, version)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:  # noqa: S310 (trusted host)
        dest.write_bytes(response.read())


# When probing for the highest version, stop after this many consecutive 404s so
# a single gap in dbt's published versions doesn't end discovery prematurely.
_DISCOVER_GAP_TOLERANCE = 3
_DISCOVER_CEILING = 100


def schema_exists(spec: ArtifactSpec, version: str) -> bool:
    """Return ``True`` if the schema for ``spec``/``version`` is published."""
    try:
        with urllib.request.urlopen(schema_url(spec, version)):  # noqa: S310
            return True
    except urllib.error.HTTPError:
        return False


def discover_versions(spec: ArtifactSpec) -> tuple[str, ...]:
    """Probe ``schemas.getdbt.com`` for every published version of ``spec``.

    Walks ``v1``, ``v2``, … and collects each version that exists, stopping once
    it sees :data:`_DISCOVER_GAP_TOLERANCE` consecutive misses (so an isolated
    gap doesn't cut discovery short).
    """
    found: list[str] = []
    misses = 0
    number = 1
    while number <= _DISCOVER_CEILING and misses < _DISCOVER_GAP_TOLERANCE:
        version = f"v{number}"
        if schema_exists(spec, version):
            found.append(version)
            misses = 0
        else:
            misses += 1
        number += 1
    return tuple(found)


def discover_all() -> dict[str, tuple[str, ...]]:
    """Return the published version tuple for every artifact family."""
    return {spec.name: discover_versions(spec) for spec in ARTIFACT_SPECS}


def render_versions(table: dict[str, tuple[str, ...]]) -> str:
    """Render the ``versions.py`` source for the given family -> versions map."""
    template = _jinja_env.get_template("versions.py.jinja")
    return template.render(families=list(table.items()))


def write_versions(table: dict[str, tuple[str, ...]]) -> None:
    """Rewrite the generated ``codegen/dbt/versions.py`` table on disk."""
    paths.VERSIONS_PATH.write_text(render_versions(table))


def reload_specs() -> tuple[ArtifactSpec, ...]:
    """Reload the version table + specs from disk and return the fresh specs.

    Used after :func:`write_versions` so a single ``--discover`` run generates
    against the versions it just discovered, not the ones imported at startup.
    """
    importlib.reload(versions_module)
    importlib.reload(artifact_spec_module)
    return artifact_spec_module.ARTIFACT_SPECS


MODELS_INIT_DOC = (
    '"""Typed pydantic models for every supported dbt artifact schema version."""\n'
)
MODELS_SUBPACKAGE_DOC = '"""Generated dbt artifact models."""\n'


def _ensure_models_packages(dest: Path) -> None:
    """Create the ``models/`` and ``models/<pkg>/`` package markers if missing."""
    models_init = paths.MODELS_DIR / "__init__.py"
    models_init.parent.mkdir(parents=True, exist_ok=True)
    if not models_init.exists():
        models_init.write_text(MODELS_INIT_DOC)
    subpackage_init = dest.parent / "__init__.py"
    subpackage_init.parent.mkdir(parents=True, exist_ok=True)
    if not subpackage_init.exists():
        subpackage_init.write_text(MODELS_SUBPACKAGE_DOC)


def generate_model(spec: ArtifactSpec, version: str) -> None:
    """Run ``datamodel-codegen`` to turn a cached schema into a model module."""
    source = resource_path(spec, version)
    dest = model_path(spec, version)
    dest.parent.mkdir(parents=True, exist_ok=True)
    _ensure_models_packages(dest)
    subprocess.run(
        [
            "datamodel-codegen",
            "--input-file-type",
            "jsonschema",
            "--target-python-version",
            TARGET_PYTHON,
            "--output-model-type",
            OUTPUT_MODEL_TYPE,
            "--disable-timestamp",
            "--formatters",
            "black",
            "isort",
            "--base-class",
            BASE_CLASS,
            "--class-name",
            model_class_name(spec, version),
            "--input",
            str(source),
            "--output",
            str(dest),
        ],
        check=True,
    )
    relax_extra_policy(dest)


def relax_extra_policy(dest: Path) -> None:
    """Rewrite ``extra="forbid"`` to ``extra="ignore"`` in a generated model.

    See :data:`_FORBID_EXTRA` for why the strict policy datamodel-codegen emits
    is loosened. A no-op if the model has no forbidding config blocks.
    """
    source = dest.read_text()
    if _FORBID_EXTRA in source:
        dest.write_text(source.replace(_FORBID_EXTRA, _IGNORE_EXTRA))


def version_map_entries(specs: tuple[ArtifactSpec, ...]) -> list[dict[str, str]]:
    """Flatten the specs into one row per (artifact, version) for templating."""
    entries: list[dict[str, str]] = []
    for spec in specs:
        for version in spec.versions:
            cls = model_class_name(spec, version)
            entries.append(
                {
                    "cls": cls,
                    "member": version_map_member(spec, version),
                    "module": (
                        f"artifact_parser.dbt.generated.models."
                        f"{spec.package}.{spec.package}_{version}"
                    ),
                    "url": f"{SCHEMA_URL_BASE}/{spec.name}/{version}.json",
                }
            )
    return entries


def render_version_map(specs: tuple[ArtifactSpec, ...]) -> str:
    """Render the full ``version_map.py`` source for the given specs."""
    template = _jinja_env.get_template("version_map.py.jinja")
    return template.render(entries=version_map_entries(specs))


def write_version_map(specs: tuple[ArtifactSpec, ...]) -> None:
    """Regenerate ``version_map.py`` from the given specs."""
    paths.VERSION_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    paths.VERSION_MAP_PATH.write_text(render_version_map(specs))


def family_context(spec: ArtifactSpec) -> dict[str, object]:
    """Build the per-artifact-family context the parser template needs."""
    const = spec.name.upper().replace("-", "_")
    versions = [
        {
            "version": version,
            "cls": model_class_name(spec, version),
            "member": version_map_member(spec, version),
        }
        for version in spec.versions
    ]
    classes = [v["cls"] for v in versions]
    union = (
        classes[0]
        if len(classes) == 1
        else "(\n    " + "\n    | ".join(classes) + "\n)"
    )
    return {
        "name": spec.name,
        "func": spec.package,
        "alias": f"{spec.class_prefix}Types",
        "const": const,
        "prefix": f"{SCHEMA_URL_BASE}/{spec.name}/",
        "union": union,
        "versions": versions,
    }


def render_parser(specs: tuple[ArtifactSpec, ...]) -> str:
    """Render the full ``parser.py`` source for the given specs."""
    template = _jinja_env.get_template("parser.py.jinja")
    families = [family_context(spec) for spec in specs]
    return template.render(
        families=families,
        model_imports=version_map_entries(specs),
    )


def write_parser(specs: tuple[ArtifactSpec, ...]) -> None:
    """Regenerate ``parser.py`` from the given specs."""
    paths.PARSER_PATH.parent.mkdir(parents=True, exist_ok=True)
    paths.PARSER_PATH.write_text(render_parser(specs))


def write_generated_init() -> None:
    """(Re)create the ``generated`` package marker so the dir can be rebuilt."""
    paths.GENERATED_INIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    template = _jinja_env.get_template("generated_init.py.jinja")
    paths.GENERATED_INIT_PATH.write_text(template.render())


def resolve_targets(
    artifact_type: str | None,
    versions: list[str],
    specs: tuple[ArtifactSpec, ...] = ARTIFACT_SPECS,
) -> list[tuple[ArtifactSpec, str]]:
    """Expand a CLI selection into concrete ``(spec, version)`` pairs.

    ``specs`` defaults to the module-level catalogue but may be passed explicitly
    (e.g. the freshly reloaded specs after ``--discover``).

    Raises:
        KeyError: if ``artifact_type`` is unknown.
        ValueError: if a requested version isn't supported for the type.
    """
    if artifact_type is None:
        return [(spec, ver) for spec in specs for ver in spec.versions]
    matches = [spec for spec in specs if spec.name == artifact_type]
    if not matches:
        valid = ", ".join(spec.name for spec in specs)
        raise KeyError(
            f"Unknown artifact type {artifact_type!r}. Valid types: {valid}."
        )
    spec = matches[0]
    chosen = versions or list(spec.versions)
    for ver in chosen:
        if ver not in spec.versions:
            raise ValueError(
                f"{spec.name} has no version {ver!r}. "
                f"Known: {', '.join(spec.versions)}."
            )
    return [(spec, ver) for ver in chosen]
