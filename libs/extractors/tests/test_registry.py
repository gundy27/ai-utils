"""Tests for ParserRegistry."""

import pytest

from gundy_ai.extractors import BaseParser, ParserManifest, ParserRegistry, ParsedChunk


class MockParserA(BaseParser):
    @property
    def manifest(self) -> ParserManifest:
        return ParserManifest(
            name="mock_a",
            version="1.0.0",
            supported_types=[".a", ".aa"],
        )

    def parse(self, file_path: str) -> list[ParsedChunk]:
        return []


class MockParserB(BaseParser):
    @property
    def manifest(self) -> ParserManifest:
        return ParserManifest(
            name="mock_b",
            version="2.0.0",
            supported_types=[".b"],
        )

    def parse(self, file_path: str) -> list[ParsedChunk]:
        return []


def test_registry_initialization():
    """Test registry initializes empty."""
    registry = ParserRegistry()
    assert registry.list_parsers() == []
    assert registry.get_supported_extensions() == []


def test_register_parser():
    """Test registering a parser."""
    registry = ParserRegistry()
    parser = MockParserA()

    registry.register(parser)

    assert len(registry.list_parsers()) == 1
    assert ".a" in registry.get_supported_extensions()
    assert ".aa" in registry.get_supported_extensions()


def test_register_multiple_parsers():
    """Test registering multiple parsers."""
    registry = ParserRegistry()

    registry.register(MockParserA())
    registry.register(MockParserB())

    assert len(registry.list_parsers()) == 2
    assert len(registry.get_supported_extensions()) == 3


def test_register_duplicate_name_fails():
    """Test that registering same parser name twice fails."""
    registry = ParserRegistry()

    registry.register(MockParserA())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(MockParserA())


def test_register_extension_conflict_fails():
    """Test that registering conflicting extension fails."""

    class ConflictingParser(BaseParser):
        @property
        def manifest(self) -> ParserManifest:
            return ParserManifest(
                name="conflict",
                version="1.0.0",
                supported_types=[".a"],  # Conflicts with MockParserA
            )

        def parse(self, file_path: str) -> list[ParsedChunk]:
            return []

    registry = ParserRegistry()
    registry.register(MockParserA())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(ConflictingParser())


def test_get_parser_by_extension():
    """Test retrieving parser by file extension."""
    registry = ParserRegistry()
    parser_a = MockParserA()
    parser_b = MockParserB()

    registry.register(parser_a)
    registry.register(parser_b)

    # Test exact match
    assert registry.get_parser(".a") == parser_a
    assert registry.get_parser(".aa") == parser_a
    assert registry.get_parser(".b") == parser_b

    # Test case insensitivity
    assert registry.get_parser(".A") == parser_a
    assert registry.get_parser(".B") == parser_b

    # Test without leading dot
    assert registry.get_parser("a") == parser_a

    # Test unknown extension
    assert registry.get_parser(".unknown") is None


def test_get_parser_by_name():
    """Test retrieving parser by name."""
    registry = ParserRegistry()
    parser_a = MockParserA()

    registry.register(parser_a)

    assert registry.get_parser_by_name("mock_a") == parser_a
    assert registry.get_parser_by_name("unknown") is None


def test_unregister_parser():
    """Test unregistering a parser."""
    registry = ParserRegistry()
    parser = MockParserA()

    registry.register(parser)
    assert len(registry.list_parsers()) == 1

    registry.unregister("mock_a")
    assert len(registry.list_parsers()) == 0
    assert registry.get_supported_extensions() == []


def test_unregister_unknown_parser_fails():
    """Test that unregistering unknown parser fails."""
    registry = ParserRegistry()

    with pytest.raises(KeyError, match="not found"):
        registry.unregister("unknown")


def test_list_parsers():
    """Test listing all parsers."""
    registry = ParserRegistry()

    registry.register(MockParserA())
    registry.register(MockParserB())

    manifests = registry.list_parsers()
    assert len(manifests) == 2

    names = [m.name for m in manifests]
    assert "mock_a" in names
    assert "mock_b" in names


def test_health_check_all():
    """Test health check for all parsers."""

    class HealthyParser(BaseParser):
        @property
        def manifest(self) -> ParserManifest:
            return ParserManifest(
                name="healthy", version="1.0.0", supported_types=[".h"]
            )

        def parse(self, file_path: str) -> list[ParsedChunk]:
            return []

        def health_check(self) -> bool:
            return True

    class UnhealthyParser(BaseParser):
        @property
        def manifest(self) -> ParserManifest:
            return ParserManifest(
                name="unhealthy", version="1.0.0", supported_types=[".u"]
            )

        def parse(self, file_path: str) -> list[ParsedChunk]:
            return []

        def health_check(self) -> bool:
            return False

    registry = ParserRegistry()
    registry.register(HealthyParser())
    registry.register(UnhealthyParser())

    results = registry.health_check_all()

    assert results["healthy"] is True
    assert results["unhealthy"] is False


def test_registry_repr():
    """Test string representation of registry."""
    registry = ParserRegistry()
    registry.register(MockParserA())

    repr_str = repr(registry)
    assert "ParserRegistry" in repr_str
    assert "parsers=1" in repr_str
