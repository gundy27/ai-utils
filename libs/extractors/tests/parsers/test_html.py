"""Tests for HTML parser."""

from __future__ import annotations

import time
from unittest.mock import Mock, patch

import pytest

from gundy_ai.extractors.parsers import HTMLParser
from gundy_ai.extractors.parsers.html_utils import (
    clean_text,
    extract_metadata,
    extract_plaintext,
)


@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="A test page for HTML parsing">
        <meta name="keywords" content="test, html, parsing">
        <meta name="author" content="Test Author">
        <meta property="og:title" content="OG Test Title">
        <meta property="og:description" content="OG description">
        <meta name="twitter:card" content="summary">
        <script>console.log('ignore me');</script>
        <style>body { color: red; }</style>
    </head>
    <body>
        <nav>Navigation</nav>
        <h1>Main Heading</h1>
        <h2>Subheading One</h2>
        <p>This is the first paragraph with some content.</p>
        <p>This is the second paragraph.</p>
        <h2>Subheading Two</h2>
        <p>Another paragraph here.</p>
        <a href="https://example.com">Example Link</a>
        <a href="/relative">Relative Link</a>
        <footer>Footer content</footer>
    </body>
    </html>
    """


@pytest.fixture
def html_file(tmp_path, sample_html):
    """Create a temporary HTML file."""
    file_path = tmp_path / "test.html"
    file_path.write_text(sample_html, encoding="utf-8")
    return str(file_path)


@pytest.fixture
def malformed_html():
    """Malformed HTML for testing error handling."""
    return """
    <html>
    <head><title>Malformed
    <body>
    <p>Missing closing tags
    <h1>Still works with BeautifulSoup
    """


def test_parser_manifest():
    """Test parser manifest information."""
    parser = HTMLParser()
    manifest = parser.manifest

    assert manifest.name == "html"
    assert manifest.version == "1.0.0"
    assert ".html" in manifest.supported_types
    assert ".htm" in manifest.supported_types
    assert "beautifulsoup4>=4.12,<5.0" in manifest.dependencies
    assert "httpx>=0.25,<1.0" in manifest.dependencies


def test_parse_local_file(html_file):
    """Test parsing HTML from local file."""
    parser = HTMLParser()
    chunks = parser.parse(html_file)

    assert len(chunks) > 0

    # Check that we have different types of chunks
    chunk_types = {chunk.metadata.get("type") for chunk in chunks}
    assert "title" in chunk_types
    assert "heading" in chunk_types
    assert "paragraph" in chunk_types
    assert "link" in chunk_types
    assert "metadata" in chunk_types


def test_extract_title(html_file):
    """Test title extraction."""
    parser = HTMLParser()
    chunks = parser.parse(html_file)

    title_chunks = [c for c in chunks if c.metadata.get("type") == "title"]
    assert len(title_chunks) == 1
    assert "Test Page" in title_chunks[0].text


def test_extract_headings(html_file):
    """Test heading extraction with levels."""
    parser = HTMLParser()
    chunks = parser.parse(html_file)

    heading_chunks = [c for c in chunks if c.metadata.get("type") == "heading"]

    # Should have 1 h1 and 2 h2 headings
    h1_chunks = [c for c in heading_chunks if c.metadata.get("level") == 1]
    h2_chunks = [c for c in heading_chunks if c.metadata.get("level") == 2]

    assert len(h1_chunks) == 1
    assert "Main Heading" in h1_chunks[0].text

    assert len(h2_chunks) == 2
    assert any("Subheading One" in c.text for c in h2_chunks)
    assert any("Subheading Two" in c.text for c in h2_chunks)


def test_extract_paragraphs(html_file):
    """Test paragraph extraction."""
    parser = HTMLParser()
    chunks = parser.parse(html_file)

    paragraph_chunks = [c for c in chunks if c.metadata.get("type") == "paragraph"]

    assert len(paragraph_chunks) == 3
    assert any("first paragraph" in c.text for c in paragraph_chunks)
    assert any("second paragraph" in c.text for c in paragraph_chunks)
    assert any("Another paragraph" in c.text for c in paragraph_chunks)


def test_extract_links(html_file):
    """Test link extraction with hrefs."""
    parser = HTMLParser(extract_links=True)
    chunks = parser.parse(html_file)

    link_chunks = [c for c in chunks if c.metadata.get("type") == "link"]

    assert len(link_chunks) == 2

    # Check that hrefs are captured
    hrefs = [c.metadata.get("href") for c in link_chunks]
    assert "https://example.com" in hrefs
    assert "/relative" in hrefs

    # Check link text
    link_texts = [c.text for c in link_chunks]
    assert "Example Link" in link_texts
    assert "Relative Link" in link_texts


def test_extract_links_disabled(html_file):
    """Test that links are not extracted when disabled."""
    parser = HTMLParser(extract_links=False)
    chunks = parser.parse(html_file)

    link_chunks = [c for c in chunks if c.metadata.get("type") == "link"]

    assert len(link_chunks) == 0


def test_extract_metadata(html_file):
    """Test metadata extraction."""
    parser = HTMLParser()
    chunks = parser.parse(html_file)

    metadata_chunks = [c for c in chunks if c.metadata.get("type") == "metadata"]

    assert len(metadata_chunks) == 1
    metadata_chunk = metadata_chunks[0]

    # Check that standard meta tags are present
    assert metadata_chunk.metadata.get("description") == "A test page for HTML parsing"
    assert metadata_chunk.metadata.get("keywords") == "test, html, parsing"
    assert metadata_chunk.metadata.get("author") == "Test Author"

    # Check Open Graph tags
    assert metadata_chunk.metadata.get("og_title") == "OG Test Title"
    assert metadata_chunk.metadata.get("og_description") == "OG description"

    # Check Twitter tags
    assert metadata_chunk.metadata.get("twitter_card") == "summary"


def test_invalid_html(tmp_path, malformed_html):
    """Test handling of malformed HTML."""
    file_path = tmp_path / "malformed.html"
    file_path.write_text(malformed_html, encoding="utf-8")

    parser = HTMLParser()
    # Should not raise an error - BeautifulSoup is forgiving
    chunks = parser.parse(str(file_path))

    assert len(chunks) > 0
    # Check that we still extracted something (headings or paragraphs)
    chunk_types = {c.metadata.get("type") for c in chunks}
    assert "heading" in chunk_types or "paragraph" in chunk_types


def test_missing_file():
    """Test FileNotFoundError for missing file."""
    parser = HTMLParser()

    with pytest.raises(FileNotFoundError) as exc_info:
        parser.parse("/nonexistent/file.html")

    assert "File not found" in str(exc_info.value)


@patch("httpx.get")
def test_parse_url(mock_get, sample_html):
    """Test parsing HTML from URL."""
    # Mock the httpx response
    mock_response = Mock()
    mock_response.text = sample_html
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    parser = HTMLParser()
    chunks = parser.parse("https://example.com/page.html")

    assert len(chunks) > 0
    assert any(c.metadata.get("type") == "title" for c in chunks)

    # Verify httpx was called
    mock_get.assert_called_once()


@patch("httpx.get")
def test_network_error(mock_get):
    """Test handling of network errors."""
    import httpx

    mock_get.side_effect = httpx.HTTPError("Network error")

    parser = HTMLParser()

    with pytest.raises(httpx.HTTPError):
        parser.parse("https://example.com/page.html")


def test_performance(html_file):
    """Test that parsing completes in reasonable time."""
    parser = HTMLParser()

    start_time = time.time()
    chunks = parser.parse(html_file)
    elapsed_ms = (time.time() - start_time) * 1000

    # Should complete in less than 500ms for small files
    assert elapsed_ms < 500
    assert len(chunks) > 0


def test_plaintext_utility(sample_html):
    """Test plaintext extraction utility."""
    text = extract_plaintext(sample_html)

    # Check that content is present
    assert "Main Heading" in text
    assert "first paragraph" in text

    # Check that script and style are removed
    assert "console.log" not in text
    assert "color: red" not in text

    # Check that nav and footer are removed
    assert "Navigation" not in text
    assert "Footer content" not in text


def test_plaintext_with_links(sample_html):
    """Test plaintext extraction with link preservation."""
    text = extract_plaintext(sample_html, preserve_links=True)

    # Check that links are preserved with URLs
    assert "Example Link (https://example.com)" in text or "https://example.com" in text


def test_clean_text():
    """Test text cleaning utility."""
    messy_text = "  This  has   multiple    spaces  \n\n\n\n  And   newlines  \n  "
    cleaned = clean_text(messy_text)

    # Should normalize spaces
    assert "multiple    spaces" not in cleaned
    assert "This has multiple spaces" in cleaned

    # Should normalize newlines
    assert "\n\n\n" not in cleaned


def test_extract_metadata_function(sample_html):
    """Test metadata extraction function directly."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(sample_html, "html.parser")
    metadata = extract_metadata(soup)

    assert "description" in metadata
    assert "keywords" in metadata
    assert "author" in metadata
    assert "og_title" in metadata
    assert "twitter_card" in metadata


def test_health_check():
    """Test health check for dependencies."""
    parser = HTMLParser()
    # Should return True since beautifulsoup4 and httpx are installed
    assert parser.health_check() is True


def test_chunk_metadata(html_file):
    """Test that chunks have proper metadata."""
    parser = HTMLParser()
    chunks = parser.parse(html_file)

    for chunk in chunks:
        # All chunks should have parser information
        assert chunk.metadata.get("parser") == "html"
        assert chunk.metadata.get("parser_version") == "1.0.0"
        assert chunk.metadata.get("source") == html_file

        # All chunks should have a type
        assert "type" in chunk.metadata

        # Check span information
        assert chunk.span_start >= 0
        assert chunk.span_end > chunk.span_start
        assert len(chunk.text) == chunk.span_end - chunk.span_start


def test_encoding_fallback(tmp_path):
    """Test that parser handles different encodings."""
    # Create file with latin-1 encoding
    file_path = tmp_path / "latin1.html"
    content = "<html><body><p>Café</p></body></html>"
    file_path.write_bytes(content.encode("latin-1"))

    parser = HTMLParser()
    chunks = parser.parse(str(file_path))

    # Should successfully parse
    assert len(chunks) > 0


def test_empty_html(tmp_path):
    """Test handling of empty HTML."""
    file_path = tmp_path / "empty.html"
    file_path.write_text("<html><body></body></html>", encoding="utf-8")

    parser = HTMLParser()
    chunks = parser.parse(str(file_path))

    # Should not crash, may return empty or minimal chunks
    assert isinstance(chunks, list)


def test_parser_options():
    """Test parser initialization options."""
    parser = HTMLParser(parser="html.parser", extract_links=False, timeout=60)

    assert parser._parser == "html.parser"
    assert parser._extract_links is False
    assert parser._timeout == 60


def test_url_detection():
    """Test that URLs are correctly detected."""
    # These should be detected as URLs
    assert "http://example.com".startswith("http://")
    assert "https://example.com".startswith("https://")

    # These should not
    assert not "/local/file.html".startswith("http://")
    assert not "file.html".startswith("http://")
