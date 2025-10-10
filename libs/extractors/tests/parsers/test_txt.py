"""Tests for TXT parser."""

import tempfile
from pathlib import Path

import pytest

from gundy_ai.extractors import ParsedChunk, TXTParser


@pytest.fixture
def txt_parser():
    """Create TXT parser instance."""
    return TXTParser()


@pytest.fixture
def sample_text_file():
    """Create a temporary text file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test document.\n")
        f.write("It has multiple lines.\n")
        f.write("And some content for testing.")
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


def test_txt_parser_manifest(txt_parser):
    """Test TXT parser manifest."""
    manifest = txt_parser.manifest

    assert manifest.name == "txt"
    assert manifest.version == "1.0.0"
    assert ".txt" in manifest.supported_types
    assert ".md" in manifest.supported_types
    assert ".csv" in manifest.supported_types
    assert manifest.schema_version == "1.0"
    assert manifest.dependencies == []


def test_txt_parser_health_check(txt_parser):
    """Test TXT parser health check."""
    assert txt_parser.health_check() is True


def test_parse_simple_text_file(txt_parser, sample_text_file):
    """Test parsing a simple text file."""
    chunks = txt_parser.parse(sample_text_file)

    assert len(chunks) == 1
    assert isinstance(chunks[0], ParsedChunk)

    chunk = chunks[0]
    assert "This is a test document" in chunk.text
    assert "multiple lines" in chunk.text
    assert "content for testing" in chunk.text
    assert chunk.span_start == 0
    assert chunk.span_end == len(chunk.text)
    assert chunk.metadata["parser"] == "txt"
    assert chunk.metadata["encoding"] == "utf-8"


def test_parse_file_not_found(txt_parser):
    """Test parsing non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="File not found"):
        txt_parser.parse("/path/to/nonexistent/file.txt")


def test_parse_empty_file(txt_parser):
    """Test parsing empty file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_path = f.name

    try:
        chunks = txt_parser.parse(temp_path)

        assert len(chunks) == 1
        assert chunks[0].text == ""
        assert chunks[0].span_start == 0
        assert chunks[0].span_end == 0
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parse_utf8_file(txt_parser):
    """Test parsing UTF-8 encoded file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", encoding="utf-8", delete=False
    ) as f:
        f.write("Hello 世界 🌍")
        temp_path = f.name

    try:
        chunks = txt_parser.parse(temp_path)

        assert len(chunks) == 1
        assert "世界" in chunks[0].text
        assert "🌍" in chunks[0].text
        assert chunks[0].metadata["encoding"] == "utf-8"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parse_latin1_file():
    """Test parsing Latin-1 encoded file."""
    parser = TXTParser(encoding="utf-8")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", encoding="latin-1", delete=False
    ) as f:
        f.write("Café résumé")
        temp_path = f.name

    try:
        chunks = parser.parse(temp_path)

        assert len(chunks) == 1
        assert (
            "Café" in chunks[0].text or "Caf" in chunks[0].text
        )  # May use fallback encoding
        assert chunks[0].metadata["encoding"] in ["utf-8", "latin-1"]
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parse_markdown_file(txt_parser):
    """Test parsing Markdown file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("# Header\n\n")
        f.write("This is **bold** text.\n")
        f.write("- List item 1\n")
        f.write("- List item 2\n")
        temp_path = f.name

    try:
        chunks = txt_parser.parse(temp_path)

        assert len(chunks) == 1
        assert "# Header" in chunks[0].text
        assert "**bold**" in chunks[0].text
        assert "List item" in chunks[0].text
        assert chunks[0].metadata["file_extension"] == ".md"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parse_csv_file(txt_parser):
    """Test parsing CSV file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        f.write("name,age,city\n")
        f.write("Alice,30,NYC\n")
        f.write("Bob,25,LA\n")
        temp_path = f.name

    try:
        chunks = txt_parser.parse(temp_path)

        assert len(chunks) == 1
        assert "name,age,city" in chunks[0].text
        assert "Alice" in chunks[0].text
        assert chunks[0].metadata["file_extension"] == ".csv"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parsed_chunk_metadata_structure(txt_parser, sample_text_file):
    """Test that metadata contains expected fields."""
    chunks = txt_parser.parse(sample_text_file)

    metadata = chunks[0].metadata
    assert "parser" in metadata
    assert "parser_version" in metadata
    assert "encoding" in metadata
    assert "file_name" in metadata
    assert "file_extension" in metadata

    assert metadata["parser"] == "txt"
    assert metadata["parser_version"] == "1.0.0"
    assert metadata["file_extension"] == ".txt"


def test_parse_large_file(txt_parser):
    """Test parsing a larger file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        # Write 100KB of text
        for i in range(10000):
            f.write(f"Line {i}: This is some content to make the file larger.\n")
        temp_path = f.name

    try:
        chunks = txt_parser.parse(temp_path)

        assert len(chunks) == 1
        assert len(chunks[0].text) > 100000
        assert "Line 0:" in chunks[0].text
        assert "Line 9999:" in chunks[0].text
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_custom_encoding():
    """Test parser with custom default encoding."""
    parser = TXTParser(encoding="latin-1")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", encoding="latin-1", delete=False
    ) as f:
        f.write("Test content")
        temp_path = f.name

    try:
        chunks = parser.parse(temp_path)
        assert len(chunks) == 1
        assert chunks[0].text == "Test content"
    finally:
        Path(temp_path).unlink(missing_ok=True)
