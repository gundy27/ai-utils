"""DOCX file parser for document extraction."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List

import structlog

from ..audit import ExtractionEventType, emit_extraction_event
from ..base import BaseParser
from ..models import ParsedChunk, ParserManifest

logger = structlog.get_logger(__name__)


class DOCXParser(BaseParser):
    """Parser for Microsoft Word documents (.docx).

    Extracts text from paragraphs and tables, handling merged cells
    to avoid duplication. Each paragraph or table row becomes a chunk.

    Example:
        parser = DOCXParser()
        chunks = parser.parse("document.docx")
        for chunk in chunks:
            print(f"{chunk.metadata['type']}: {chunk.text[:50]}")
    """

    def __init__(self):
        """Initialize DOCX parser."""
        logger.debug("docx_parser_initialized")

    @property
    def manifest(self) -> ParserManifest:
        """Get parser manifest."""
        return ParserManifest(
            name="docx",
            version="1.0.0",
            supported_types=[".docx"],
            schema_version="1.0",
            dependencies=["python-docx>=1.0"],
        )

    def parse(self, file_path: str) -> List[ParsedChunk]:
        """Extract text from DOCX file.

        Processes paragraphs and tables separately to maintain structure.
        Avoids duplication from merged table cells.

        Args:
            file_path: Path to DOCX file

        Returns:
            List of ParsedChunk objects (paragraphs and table rows)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a valid DOCX
            RuntimeError: If python-docx is not installed or extraction fails
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

        # Import python-docx (late import to allow package to load even if not installed)
        try:
            from docx import Document
        except ImportError as e:
            error_msg = "python-docx library is required for DOCX parsing. Install with: pip install python-docx>=1.0"
            logger.error("python_docx_not_installed", error=str(e))

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

        # Parse DOCX
        try:
            doc = Document(str(path))

            logger.info(
                "docx_parsing_started",
                file_path=file_path,
                paragraphs=len(doc.paragraphs),
                tables=len(doc.tables),
            )

            chunks = []
            char_offset = 0

            # Track elements in document order
            # Note: python-docx doesn't preserve exact ordering between paragraphs and tables
            # For simplicity, we process all paragraphs first, then all tables

            # Extract paragraphs
            for para_idx, paragraph in enumerate(doc.paragraphs):
                text = paragraph.text.strip()

                if not text:
                    continue  # Skip empty paragraphs

                chunk = ParsedChunk(
                    text=text,
                    span_start=char_offset,
                    span_end=char_offset + len(text),
                    metadata={
                        "parser": self.manifest.name,
                        "parser_version": self.manifest.version,
                        "type": "paragraph",
                        "index": para_idx,
                        "file_name": path.name,
                        "file_extension": path.suffix,
                    },
                )

                chunks.append(chunk)
                char_offset += len(text)

                logger.debug(
                    "paragraph_extracted",
                    index=para_idx,
                    characters=len(text),
                )

            # Extract tables
            for table_idx, table in enumerate(doc.tables):
                for row_idx, row in enumerate(table.rows):
                    row_texts = []
                    seen_cell_elements = set()

                    for cell in row.cells:
                        # Use cell._element to detect merged cells
                        # Merged cells will have the same _element reference
                        cell_element_id = id(cell._element)

                        if cell_element_id not in seen_cell_elements:
                            seen_cell_elements.add(cell_element_id)
                            cell_text = cell.text.strip()
                            if cell_text:
                                row_texts.append(cell_text)

                    if row_texts:
                        text = " | ".join(row_texts)

                        chunk = ParsedChunk(
                            text=text,
                            span_start=char_offset,
                            span_end=char_offset + len(text),
                            metadata={
                                "parser": self.manifest.name,
                                "parser_version": self.manifest.version,
                                "type": "table_row",
                                "table_index": table_idx,
                                "row_index": row_idx,
                                "file_name": path.name,
                                "file_extension": path.suffix,
                            },
                        )

                        chunks.append(chunk)
                        char_offset += len(text)

                logger.debug(
                    "table_extracted",
                    table_index=table_idx,
                    rows=len(table.rows),
                )

            total_characters = sum(len(chunk.text) for chunk in chunks)
            processing_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "docx_extraction_complete",
                file_path=file_path,
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
                metadata={
                    "paragraphs": len(doc.paragraphs),
                    "tables": len(doc.tables),
                },
            )

            return chunks

        except Exception as e:
            error_msg = f"Failed to parse DOCX: {str(e)}"
            logger.error(
                "docx_parsing_failed",
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
        """Check if python-docx is available.

        Returns:
            True if python-docx can be imported, False otherwise
        """
        from importlib.util import find_spec

        is_available = find_spec("docx") is not None
        if not is_available:
            logger.warning("docx_parser_unhealthy", reason="python-docx not installed")
        return is_available
