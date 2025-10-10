"""Tests for BaseParser interface."""

from gundy_ai.extractors import BaseParser, ParsedChunk, ParserManifest


class MockParser(BaseParser):
    """Mock parser for testing interface."""

    @property
    def manifest(self) -> ParserManifest:
        return ParserManifest(
            name="mock",
            version="1.0.0",
            supported_types=[".mock"],
        )

    def parse(self, file_path: str) -> list[ParsedChunk]:
        return [
            ParsedChunk(
                text="mock content",
                span_start=0,
                span_end=12,
                metadata={"parser": "mock"},
            )
        ]


def test_base_parser_interface():
    """Test that BaseParser interface can be implemented."""
    parser = MockParser()
    assert parser.manifest.name == "mock"
    assert parser.manifest.version == "1.0.0"
    assert ".mock" in parser.manifest.supported_types


def test_base_parser_parse():
    """Test that parse method returns ParsedChunk objects."""
    parser = MockParser()
    chunks = parser.parse("test.mock")

    assert len(chunks) == 1
    assert isinstance(chunks[0], ParsedChunk)
    assert chunks[0].text == "mock content"
    assert chunks[0].span_start == 0
    assert chunks[0].span_end == 12


def test_base_parser_health_check():
    """Test default health_check implementation."""
    parser = MockParser()
    assert parser.health_check() is True


def test_parser_repr():
    """Test string representation."""
    parser = MockParser()
    repr_str = repr(parser)
    assert "MockParser" in repr_str
    assert "mock" in repr_str
