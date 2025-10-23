"""HTML file parser for document extraction."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, List

import structlog

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

from ..audit import ExtractionEventType, emit_extraction_event
from ..base import BaseParser
from ..models import ParsedChunk, ParserManifest
from .html_utils import clean_text, extract_metadata, fetch_html

logger = structlog.get_logger(__name__)


class HTMLParser(BaseParser):
    """Parser for HTML documents.

    Extracts structured content including title, headings, paragraphs,
    links, and metadata from HTML files or URLs. Can handle both local
    files and remote URLs.

    Example:
        # Parse local file
        parser = HTMLParser()
        chunks = parser.parse("document.html")

        # Parse URL
        chunks = parser.parse("https://example.com")

        # Without links
        parser = HTMLParser(extract_links=False)
        chunks = parser.parse("document.html")
    """

    def __init__(
        self, parser: str = "html.parser", extract_links: bool = True, timeout: int = 30
    ):
        """Initialize HTML parser.

        Args:
            parser: BeautifulSoup parser engine (default: "html.parser")
                   Options: "html.parser", "lxml", "html5lib"
            extract_links: Whether to extract links as separate chunks (default: True)
            timeout: Timeout for URL fetching in seconds (default: 30)
        """
        self._parser = parser
        self._extract_links = extract_links
        self._timeout = timeout
        logger.debug(
            "html_parser_initialized",
            parser=parser,
            extract_links=extract_links,
            timeout=timeout,
        )

    @property
    def manifest(self) -> ParserManifest:
        """Get parser manifest."""
        return ParserManifest(
            name="html",
            version="1.0.0",
            supported_types=[".html", ".htm"],
            schema_version="1.0",
            dependencies=["beautifulsoup4>=4.12,<5.0", "httpx>=0.25,<1.0"],
        )

    def parse(self, file_path: str) -> List[ParsedChunk]:
        """Extract structured content from HTML file or URL.

        Args:
            file_path: Path to HTML file or URL (starting with http:// or https://)

        Returns:
            List of ParsedChunk objects containing:
            - Title chunk (type: "title")
            - Heading chunks (type: "heading", with level 1-6)
            - Paragraph chunks (type: "paragraph")
            - Link chunks if extract_links=True (type: "link", with href)
            - Metadata chunk (type: "metadata")

        Raises:
            FileNotFoundError: If local file doesn't exist
            ValueError: If file is not valid HTML
            RuntimeError: If beautifulsoup4 is not installed or parsing fails
            httpx.HTTPError: If URL fetching fails
        """
        start_time = time.time()
        is_url = file_path.startswith("http://") or file_path.startswith("https://")

        # Emit invoked event
        emit_extraction_event(
            event_type=ExtractionEventType.EXTRACTOR_INVOKED,
            parser_name=self.manifest.name,
            file_path=file_path,
            outcome="pending",
            parser_version=self.manifest.version,
            metadata={"is_url": is_url},
        )

        try:
            # Get HTML content
            if is_url:
                html_content = self._fetch_from_url(file_path)
            else:
                html_content = self._read_from_file(file_path)

            # Parse HTML
            soup = self._create_soup(html_content)

            # Extract chunks
            chunks = self._extract_chunks(soup, file_path)

            processing_time_ms = (time.time() - start_time) * 1000
            total_chars = sum(len(chunk.text) for chunk in chunks)

            logger.info(
                "html_extraction_complete",
                file_path=file_path,
                is_url=is_url,
                chunks=len(chunks),
                characters=total_chars,
                processing_time_ms=processing_time_ms,
            )

            # Emit success event
            emit_extraction_event(
                event_type=ExtractionEventType.EXTRACTOR_SUCCEEDED,
                parser_name=self.manifest.name,
                file_path=file_path,
                outcome="success",
                parser_version=self.manifest.version,
                processing_time_ms=processing_time_ms,
                chunks_extracted=len(chunks),
                total_characters=total_chars,
                metadata={"is_url": is_url},
            )

            return chunks

        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            logger.error(
                "html_extraction_failed",
                file_path=file_path,
                error=str(e),
                processing_time_ms=processing_time_ms,
            )

            # Emit failure event
            emit_extraction_event(
                event_type=ExtractionEventType.EXTRACTOR_FAILED,
                parser_name=self.manifest.name,
                file_path=file_path,
                outcome="failure",
                parser_version=self.manifest.version,
                error_message=str(e),
                processing_time_ms=processing_time_ms,
            )

            raise

    def _read_from_file(self, file_path: str) -> str:
        """Read HTML content from local file.

        Args:
            file_path: Path to HTML file

        Returns:
            HTML content as string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error("file_not_found", file_path=file_path)
            raise FileNotFoundError(error_msg)

        try:
            content = path.read_text(encoding="utf-8")
            logger.debug("file_read_success", file_path=file_path, size=len(content))
            return content
        except UnicodeDecodeError:
            # Try with latin-1 as fallback
            try:
                content = path.read_text(encoding="latin-1")
                logger.debug(
                    "file_read_success_fallback",
                    file_path=file_path,
                    encoding="latin-1",
                    size=len(content),
                )
                return content
            except Exception as e:
                error_msg = (
                    f"Could not read file with any supported encoding: {file_path}"
                )
                logger.error("file_read_failed", file_path=file_path, error=str(e))
                raise ValueError(error_msg) from e

    def _fetch_from_url(self, url: str) -> str:
        """Fetch HTML content from URL.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            httpx.HTTPError: If request fails
        """
        logger.debug("fetching_url", url=url)
        return fetch_html(url, timeout=self._timeout)

    def _create_soup(self, html_content: str) -> "BeautifulSoup":
        """Create BeautifulSoup object from HTML content.

        Args:
            html_content: Raw HTML string

        Returns:
            BeautifulSoup object

        Raises:
            ImportError: If beautifulsoup4 is not installed
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError as e:
            error_msg = (
                "beautifulsoup4 library is required for HTML parsing. "
                "Install with: pip install beautifulsoup4>=4.12"
            )
            logger.error("beautifulsoup_not_installed", error=str(e))
            raise ImportError(error_msg) from e

        return BeautifulSoup(html_content, self._parser)

    def _extract_chunks(self, soup: "BeautifulSoup", source: str) -> List[ParsedChunk]:
        """Extract structured chunks from parsed HTML.

        Args:
            soup: BeautifulSoup object
            source: Source file path or URL for metadata

        Returns:
            List of ParsedChunk objects
        """
        chunks: List[ParsedChunk] = []
        char_offset = 0

        # Extract title
        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            title_text = clean_text(title_tag.string)
            if title_text:
                chunks.append(
                    ParsedChunk(
                        text=title_text,
                        span_start=char_offset,
                        span_end=char_offset + len(title_text),
                        metadata={
                            "type": "title",
                            "parser": self.manifest.name,
                            "parser_version": self.manifest.version,
                            "source": source,
                        },
                    )
                )
                char_offset += len(title_text) + 1

        # Extract headings (h1-h6)
        for level in range(1, 7):
            heading_tags = soup.find_all(f"h{level}")
            for tag in heading_tags:
                heading_text = clean_text(tag.get_text())
                if heading_text:
                    chunks.append(
                        ParsedChunk(
                            text=heading_text,
                            span_start=char_offset,
                            span_end=char_offset + len(heading_text),
                            metadata={
                                "type": "heading",
                                "level": level,
                                "parser": self.manifest.name,
                                "parser_version": self.manifest.version,
                                "source": source,
                            },
                        )
                    )
                    char_offset += len(heading_text) + 1

        # Extract paragraphs
        paragraph_tags = soup.find_all("p")
        for tag in paragraph_tags:
            para_text = clean_text(tag.get_text())
            if para_text:
                chunks.append(
                    ParsedChunk(
                        text=para_text,
                        span_start=char_offset,
                        span_end=char_offset + len(para_text),
                        metadata={
                            "type": "paragraph",
                            "parser": self.manifest.name,
                            "parser_version": self.manifest.version,
                            "source": source,
                        },
                    )
                )
                char_offset += len(para_text) + 1

        # Extract links (optional)
        if self._extract_links:
            link_tags = soup.find_all("a")
            for tag in link_tags:
                href = tag.get("href")
                link_text = clean_text(tag.get_text())
                if link_text and href:
                    chunks.append(
                        ParsedChunk(
                            text=link_text,
                            span_start=char_offset,
                            span_end=char_offset + len(link_text),
                            metadata={
                                "type": "link",
                                "href": href,
                                "parser": self.manifest.name,
                                "parser_version": self.manifest.version,
                                "source": source,
                            },
                        )
                    )
                    char_offset += len(link_text) + 1

        # Extract metadata
        metadata = extract_metadata(soup)
        if metadata:
            # Create a text representation of metadata
            meta_text = "\n".join(f"{k}: {v}" for k, v in metadata.items())
            chunks.append(
                ParsedChunk(
                    text=meta_text,
                    span_start=char_offset,
                    span_end=char_offset + len(meta_text),
                    metadata={
                        "type": "metadata",
                        "parser": self.manifest.name,
                        "parser_version": self.manifest.version,
                        "source": source,
                        **metadata,
                    },
                )
            )

        return chunks

    def health_check(self) -> bool:
        """Check if parser dependencies are available.

        Returns:
            True if beautifulsoup4 and httpx are installed, False otherwise
        """
        try:
            import bs4  # noqa: F401
            import httpx  # noqa: F401

            return True
        except ImportError:
            return False
