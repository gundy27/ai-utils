"""Tests for PDF parser."""

import tempfile
from pathlib import Path

import pytest

from gundy_ai.extractors import ParsedChunk, PDFParser


@pytest.fixture
def pdf_parser():
    """Create PDF parser instance."""
    return PDFParser()


def test_pdf_parser_manifest(pdf_parser):
    """Test PDF parser manifest."""
    manifest = pdf_parser.manifest

    assert manifest.name == "pdf"
    assert manifest.version == "1.0.0"
    assert ".pdf" in manifest.supported_types
    assert manifest.schema_version == "1.0"
    assert "pypdf>=3.0" in manifest.dependencies


def test_pdf_parser_health_check(pdf_parser):
    """Test PDF parser health check."""
    # Should be True since pypdf is installed
    assert pdf_parser.health_check() is True


def test_parse_file_not_found(pdf_parser):
    """Test parsing non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="File not found"):
        pdf_parser.parse("/path/to/nonexistent/file.pdf")


def test_parse_simple_pdf(pdf_parser):
    """Test parsing a simple PDF file.

    Note: This test creates a minimal PDF using pypdf.
    For real-world testing, use actual PDF files.
    """
    from pypdf import PdfWriter

    # Create a simple PDF with one page
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        writer.write(f)
        temp_path = f.name

    try:
        chunks = pdf_parser.parse(temp_path)

        # Should have 1 chunk (1 page)
        assert len(chunks) == 1
        assert isinstance(chunks[0], ParsedChunk)

        chunk = chunks[0]
        assert chunk.span_start == 0
        assert chunk.metadata["parser"] == "pdf"
        assert chunk.metadata["page"] == 1
        assert chunk.metadata["total_pages"] == 1
        assert chunk.metadata["file_extension"] == ".pdf"
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parse_multipage_pdf(pdf_parser):
    """Test parsing a multi-page PDF."""
    from pypdf import PdfWriter

    # Create a 3-page PDF
    writer = PdfWriter()
    for i in range(3):
        writer.add_blank_page(width=200, height=200)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        writer.write(f)
        temp_path = f.name

    try:
        chunks = pdf_parser.parse(temp_path)

        # Should have 3 chunks (3 pages)
        assert len(chunks) == 3

        # Check page numbers
        for i, chunk in enumerate(chunks, start=1):
            assert chunk.metadata["page"] == i
            assert chunk.metadata["total_pages"] == 3

        # Check spans are sequential
        assert chunks[0].span_start == 0
        assert chunks[1].span_start == chunks[0].span_end
        assert chunks[2].span_start == chunks[1].span_end
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parse_invalid_pdf(pdf_parser):
    """Test parsing invalid PDF file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".pdf", delete=False) as f:
        f.write("This is not a PDF file")
        temp_path = f.name

    try:
        with pytest.raises(RuntimeError, match="Failed to parse PDF"):
            pdf_parser.parse(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_parsed_chunk_metadata_structure(pdf_parser):
    """Test that chunks have expected metadata."""
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        writer.write(f)
        temp_path = f.name

    try:
        chunks = pdf_parser.parse(temp_path)

        metadata = chunks[0].metadata
        assert "parser" in metadata
        assert "parser_version" in metadata
        assert "page" in metadata
        assert "total_pages" in metadata
        assert "file_name" in metadata
        assert "file_extension" in metadata

        assert metadata["parser"] == "pdf"
        assert metadata["parser_version"] == "1.0.0"
        assert metadata["file_extension"] == ".pdf"
    finally:
        Path(temp_path).unlink(missing_ok=True)
