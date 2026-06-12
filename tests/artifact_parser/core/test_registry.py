"""Tests for the framework registry and the plugin protocol."""

import pytest

from artifact_parser.core.base import BaseArtifactModel
from artifact_parser.core.exceptions import ParserRegistrationError
from artifact_parser.core.exceptions import UnknownArtifactError
from artifact_parser.core.parser import ArtifactParser
from artifact_parser.core.registry import ParserRegistry


class _StubModel(BaseArtifactModel):
    value: str


class _StubParser(ArtifactParser):
    """A toy parser that claims artifacts carrying ``{"kind": "stub"}``."""

    name = "stub"

    def can_parse(self, artifact: dict) -> bool:
        return artifact.get("kind") == "stub"

    def parse(self, artifact: dict) -> BaseArtifactModel:
        return _StubModel(value=artifact["value"])


class _OtherParser(_StubParser):
    name = "other"

    def can_parse(self, artifact: dict) -> bool:
        return False


@pytest.fixture
def empty_registry() -> ParserRegistry:
    return ParserRegistry()


def test_register_and_get(empty_registry: ParserRegistry) -> None:
    parser = _StubParser()
    empty_registry.register(parser)
    assert empty_registry.get("stub") is parser
    assert empty_registry.names() == ["stub"]


def test_register_duplicate_name_raises(empty_registry: ParserRegistry) -> None:
    empty_registry.register(_StubParser())
    with pytest.raises(ParserRegistrationError, match="already registered"):
        empty_registry.register(_StubParser())


def test_unregister(empty_registry: ParserRegistry) -> None:
    empty_registry.register(_StubParser())
    empty_registry.unregister("stub")
    assert empty_registry.names() == []


def test_unregister_unknown_raises(empty_registry: ParserRegistry) -> None:
    with pytest.raises(UnknownArtifactError, match="No parser named 'stub'"):
        empty_registry.unregister("stub")


def test_get_unknown_raises(empty_registry: ParserRegistry) -> None:
    with pytest.raises(UnknownArtifactError, match="No parser named 'stub'"):
        empty_registry.get("stub")


def test_parse_dispatches_to_first_match(empty_registry: ParserRegistry) -> None:
    empty_registry.register(_OtherParser())
    empty_registry.register(_StubParser())
    model = empty_registry.parse({"kind": "stub", "value": "hi"})
    assert isinstance(model, _StubModel)
    assert model.value == "hi"


def test_parse_no_match_raises(empty_registry: ParserRegistry) -> None:
    empty_registry.register(_StubParser())
    with pytest.raises(UnknownArtifactError, match="Tried: stub"):
        empty_registry.parse({"kind": "nope"})


def test_parse_empty_registry_message() -> None:
    with pytest.raises(UnknownArtifactError, match=r"\(none registered\)"):
        ParserRegistry().parse({})
