"""Shared base model for every parsed artifact, regardless of source."""

from pydantic import BaseModel


class BaseArtifactModel(BaseModel):
    """Base class for all artifact models across every parser plugin.

    Each plugin (dbt-core today, others tomorrow) builds its typed models on
    top of this so the framework has a single, predictable root type to reason
    about. It is intentionally empty — it exists to be an anchor, not a place to
    smuggle behaviour into.
    """
