"""PDF file parser for document extraction."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List

import structlog

from ..audit import ExtractionEventType, emit_extraction_event
from ..base import BaseParser
from ..models import ParsedChunk, ParserManifest

logger = structlog.get_logger(__name__)


class PDFParser(BaseParser):
    """Parser for PDF documents.

    Extracts text page by page using pypdf library.
    Each page becomes a separate chunk with page metadata.

    Example:
        parser = PDFParser()
        chunks = parser.parse("document.pdf")
        for chunk in chunks:
            print(f"Page {chunk.metadata['page']}: {chunk.text[:100]}")
    """

    def __init__(self):
        """Initialize PDF parser."""
        logger.debug("pdf_parser_initialized")

    @property
    def manifest(self) -> ParserManifest:
        """Get parser manifest."""
        return ParserManifest(
            name="pdf",
            version="1.0.0",
            supported_types=[".pdf"],
            schema_version="1.0",
            dependencies=["pypdf>=3.0"],
        )

    def parse(self, file_path: str) -> List[ParsedChunk]:
        """Extract text from PDF file page by page.

        Args:
            file_path: Path to PDF file

        Returns:
            List of ParsedChunk objects, one per page

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid PDF
            RuntimeError: If pypdf is not installed or extraction fails
        """
        start_time = time.time()
        path = Path(file_path)

        # Emit invoked event
        emit_extraction_event(
            event_type=ExtractionEventType.EXTRACTOR_INVOKED,
            parser_name=self.manifest.name,
            file_path=file_path,
            outcome="pending",
            parser_version=self.manifest.version,
        )

        # Check file exists
        if not path.exists():
            error_msg = f"File not found: {file_path}"
            logger.error("file_not_found", file_path=file_path)

            emit_extraction_event(
                event_type=ExtractionEventType.EXTRACTOR_FAILED,
                parser_name=self.manifest.name,
                file_path=file_path,
                outcome="failure",
                parser_version=self.manifest.version,
                error_message=error_msg,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

            raise FileNotFoundError(error_msg)

        # Import pypdf (late import to allow package to load even if pypdf not installed)
        try:
            from pypdf import PdfReader
        except ImportError as e:
            error_msg = "pypdf library is required for PDF parsing. Install with: pip install pypdf>=3.0"
            logger.error("pypdf_not_installed", error=str(e))

            emit_extraction_event(
                event_type=ExtractionEventType.EXTRACTOR_FAILED,
                parser_name=self.manifest.name,
                file_path=file_path,
                outcome="error",
                parser_version=self.manifest.version,
                error_message=error_msg,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

            raise RuntimeError(error_msg) from e

        # Parse PDF
        try:
            reader = PdfReader(str(path))
            total_pages = len(reader.pages)

            logger.info(
                "pdf_parsing_started",
                file_path=file_path,
                total_pages=total_pages,
            )

            chunks = []
            char_offset = 0

            for page_num, page in enumerate(reader.pages, start=1):
                # Extract text from page
                page_text = page.extract_text()

                if not page_text:
                    logger.warning(
                        "empty_page",
                        file_path=file_path,
                        page=page_num,
                    )
                    page_text = ""

                # Create chunk for this page
                chunk = ParsedChunk(
                    text=page_text,
                    span_start=char_offset,
                    span_end=char_offset + len(page_text),
                    metadata={
                        "parser": self.manifest.name,
                        "parser_version": self.manifest.version,
                        "page": page_num,
                        "total_pages": total_pages,
                        "file_name": path.name,
                        "file_extension": path.suffix,
                    },
                )

                chunks.append(chunk)
                char_offset += len(page_text)

                logger.debug(
                    "page_extracted",
                    page=page_num,
                    characters=len(page_text),
                )

            total_characters = sum(len(chunk.text) for chunk in chunks)
            processing_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "pdf_extraction_complete",
                file_path=file_path,
                pages=total_pages,
                chunks=len(chunks),
                characters=total_characters,
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
                total_characters=total_characters,
                metadata={"total_pages": total_pages},
            )

            return chunks

        except Exception as e:
            error_msg = f"Failed to parse PDF: {str(e)}"
            logger.error(
                "pdf_parsing_failed",
                file_path=file_path,
                error=str(e),
            )

            emit_extraction_event(
                event_type=ExtractionEventType.EXTRACTOR_FAILED,
                parser_name=self.manifest.name,
                file_path=file_path,
                outcome="error",
                parser_version=self.manifest.version,
                error_message=error_msg,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

            raise RuntimeError(error_msg) from e

    def health_check(self) -> bool:
        """Check if pypdf is available.

        Returns:
            True if pypdf can be imported, False otherwise
        """
        from importlib.util import find_spec

        is_available = find_spec("pypdf") is not None
        if not is_available:
            logger.warning("pdf_parser_unhealthy", reason="pypdf not installed")
        return is_available
