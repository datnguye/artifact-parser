"""Single source of truth: which dbt artifacts and versions we generate.

The artifact *families* (their names, package stems, and class prefixes) are
stable and hand-written here. The per-family *versions* are discovered from
``schemas.getdbt.com`` and live in the generated :mod:`codegen.dbt.versions`
table — refresh them with ``codegen dbt --discover``.
"""

from dataclasses import dataclass

from codegen.dbt.versions import VERSIONS


@dataclass(frozen=True)
class ArtifactSpec:
    """Everything codegen needs to know about one dbt artifact family.

    Attributes:
        name: The dbt artifact name as it appears in schema URLs and filenames
            (e.g. ``"run-results"`` — hyphenated, matching dbt).
        package: The Python-safe directory/module stem (e.g. ``"run_results"``).
        class_prefix: The generated model class prefix (e.g. ``"RunResults"``).
    """

    name: str
    package: str
    class_prefix: str

    @property
    def versions(self) -> tuple[str, ...]:
        """The schema versions published for this family (low to high)."""
        return VERSIONS.get(self.name, ())


# The catalogue of dbt artifact families. Mirrors dbt's schemas/dbt/ tree; the
# version list per family is discovered into codegen.dbt.versions.
ARTIFACT_SPECS: tuple[ArtifactSpec, ...] = (
    ArtifactSpec(name="catalog", package="catalog", class_prefix="Catalog"),
    ArtifactSpec(name="manifest", package="manifest", class_prefix="Manifest"),
    ArtifactSpec(name="run-results", package="run_results", class_prefix="RunResults"),
    ArtifactSpec(name="sources", package="sources", class_prefix="Sources"),
)


def get_spec(name: str) -> ArtifactSpec:
    """Return the :class:`ArtifactSpec` whose ``name`` matches ``name``.

    Raises:
        KeyError: if no spec has that name.
    """
    for spec in ARTIFACT_SPECS:
        if spec.name == name:
            return spec
    valid = ", ".join(spec.name for spec in ARTIFACT_SPECS)
    raise KeyError(f"Unknown artifact type {name!r}. Valid types: {valid}.")
