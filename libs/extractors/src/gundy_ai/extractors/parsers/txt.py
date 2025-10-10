"""Text file parser for plain text documents."""

from __future__ import annotations

import time
from pathlib import Path
from typing import List

import structlog

from ..audit import ExtractionEventType, emit_extraction_event
from ..base import BaseParser
from ..models import ParsedChunk, ParserManifest

logger = structlog.get_logger(__name__)


class TXTParser(BaseParser):
    """Parser for plain text files (.txt, .md, .csv).

    Reads the entire file and returns it as a single chunk.
    Supports multiple encodings with automatic fallback.

    Example:
        parser = TXTParser()
        chunks = parser.parse("document.txt")
        print(chunks[0].text)
    """

    SUPPORTED_ENCODINGS = ["utf-8", "utf-16", "latin-1", "cp1252"]

    def __init__(self, encoding: str = "utf-8"):
        """Initialize TXT parser.

        Args:
            encoding: Default encoding to try first (default: utf-8)
        """
        self._encoding = encoding
        logger.debug("txt_parser_initialized", default_encoding=encoding)

    @property
    def manifest(self) -> ParserManifest:
        """Get parser manifest."""
        return ParserManifest(
            name="txt",
            version="1.0.0",
            supported_types=[".txt", ".md", ".csv", ".log"],
            schema_version="1.0",
            dependencies=[],
        )

    def parse(self, file_path: str) -> List[ParsedChunk]:
        """Extract text from a plain text file.

        Args:
            file_path: Path to text file

        Returns:
            List containing single ParsedChunk with entire file content

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be read with any supported encoding
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

        # Try to read file with various encodings
        text = None
        encoding_used = None

        # Try specified encoding first
        encodings_to_try = [self._encoding] + [
            enc for enc in self.SUPPORTED_ENCODINGS if enc != self._encoding
        ]

        for encoding in encodings_to_try:
            try:
                text = path.read_text(encoding=encoding)
                encoding_used = encoding
                logger.debug(
                    "file_read_success",
                    file_path=file_path,
                    encoding=encoding,
                    size=len(text),
                )
                break
            except (UnicodeDecodeError, LookupError) as e:
                logger.debug(
                    "encoding_failed",
                    file_path=file_path,
                    encoding=encoding,
                    error=str(e),
                )
                continue

        if text is None:
            error_msg = (
                f"Could not read file with any supported encoding: {file_path}. "
                f"Tried: {', '.join(encodings_to_try)}"
            )
            logger.error("all_encodings_failed", file_path=file_path)

            emit_extraction_event(
                event_type=ExtractionEventType.EXTRACTOR_FAILED,
                parser_name=self.manifest.name,
                file_path=file_path,
                outcome="failure",
                parser_version=self.manifest.version,
                error_message=error_msg,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

            raise ValueError(error_msg)

        # Create single chunk with entire content
        chunk = ParsedChunk(
            text=text,
            span_start=0,
            span_end=len(text),
            metadata={
                "parser": self.manifest.name,
                "parser_version": self.manifest.version,
                "encoding": encoding_used,
                "file_name": path.name,
                "file_extension": path.suffix,
            },
        )

        processing_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "text_extraction_complete",
            file_path=file_path,
            encoding=encoding_used,
            characters=len(text),
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
            chunks_extracted=1,
            total_characters=len(text),
            metadata={"encoding": encoding_used},
        )

        return [chunk]

    def health_check(self) -> bool:
        """Check if parser is ready to use.

        For TXT parser, always returns True as no external dependencies.

        Returns:
            True
        """
        return True
