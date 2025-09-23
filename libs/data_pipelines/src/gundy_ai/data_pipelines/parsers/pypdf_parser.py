"""PyPDF2-based PDF parser."""

import asyncio
import time
from pathlib import Path

from PyPDF2 import PdfReader
from PyPDF2.errors import PdfReadError

from .base import BoundingBox, PDFPage, PDFParser, PDFParsingResult, TextElement


class PyPDFParser(PDFParser):
    """PDF parser using PyPDF2 library."""

    def __init__(self):
        """Initialize PyPDF parser."""
        super().__init__("pypdf")

    def can_handle(self, file_path: str | Path) -> bool:
        """Check if PyPDF2 can handle this file."""
        if not self._validate_pdf(file_path):
            return False

        try:
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                # Try to access first page to validate
                if len(reader.pages) > 0:
                    _ = reader.pages[0].extract_text()
                return True
        except (PdfReadError, Exception) as e:
            self.logger.debug(
                "pypdf_cannot_handle", file_path=str(file_path), error=str(e)
            )
            return False

    async def parse(self, file_path: str | Path) -> PDFParsingResult:
        """Parse PDF using PyPDF2."""
        start_time = time.time()

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._parse_sync, file_path
            )

            processing_time = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time
            result.parser_used = self.name

            return result

        except Exception as e:
            self.logger.error(
                "pypdf_parse_error", file_path=str(file_path), error=str(e)
            )
            return PDFParsingResult(
                success=False,
                error=f"PyPDF parsing failed: {str(e)}",
                parser_used=self.name,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_sync(self, file_path: str | Path) -> PDFParsingResult:
        """Synchronous PDF parsing."""
        path = Path(file_path)
        pages = []

        with open(path, "rb") as f:
            reader = PdfReader(f)

            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()

                    # Get page dimensions if available
                    mediabox = page.mediabox
                    width = (
                        float(mediabox.width) if mediabox else 612.0
                    )  # Default letter width
                    height = (
                        float(mediabox.height) if mediabox else 792.0
                    )  # Default letter height

                    # Create basic text element (PyPDF2 doesn't provide positioning)
                    elements = []
                    if text.strip():
                        elements.append(
                            TextElement(
                                text=text,
                                bbox=BoundingBox(0, 0, width, height),
                                confidence=0.8,  # Lower confidence since no positioning
                            )
                        )

                    pdf_page = PDFPage(
                        page_number=page_num + 1,
                        text=text,
                        width=width,
                        height=height,
                        elements=elements,
                        metadata={
                            "extraction_method": "pypdf2",
                            "has_positioning": False,
                        },
                    )

                    pages.append(pdf_page)

                except Exception as e:
                    self.logger.warning(
                        "pypdf_page_error", page_num=page_num + 1, error=str(e)
                    )
                    # Add empty page to maintain page numbering
                    pages.append(
                        PDFPage(
                            page_number=page_num + 1,
                            text="",
                            width=612.0,
                            height=792.0,
                            metadata={"extraction_error": str(e)},
                        )
                    )

            # Extract document metadata
            metadata = {}
            if reader.metadata:
                metadata.update(
                    {
                        "title": reader.metadata.get("/Title", ""),
                        "author": reader.metadata.get("/Author", ""),
                        "subject": reader.metadata.get("/Subject", ""),
                        "creator": reader.metadata.get("/Creator", ""),
                        "producer": reader.metadata.get("/Producer", ""),
                        "creation_date": str(reader.metadata.get("/CreationDate", "")),
                        "modification_date": str(reader.metadata.get("/ModDate", "")),
                    }
                )

            metadata.update(
                {
                    "page_count": len(pages),
                    "file_size": path.stat().st_size,
                    "parser": "pypdf2",
                    "encrypted": reader.is_encrypted,
                }
            )

            return PDFParsingResult(success=True, pages=pages, metadata=metadata)
