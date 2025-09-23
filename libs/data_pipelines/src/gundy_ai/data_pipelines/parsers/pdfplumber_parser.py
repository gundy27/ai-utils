"""PDFPlumber-based PDF parser with advanced layout detection."""

import asyncio
import time
from pathlib import Path
from typing import Any

import pdfplumber

from .base import BoundingBox, PDFPage, PDFParser, PDFParsingResult, TextElement


class PDFPlumberParser(PDFParser):
    """PDF parser using pdfplumber library for better layout detection."""

    def __init__(
        self,
        extract_tables: bool = True,
        preserve_layout: bool = True,
        x_tolerance: float = 3,
        y_tolerance: float = 3,
    ):
        """Initialize PDFPlumber parser.

        Args:
            extract_tables: Whether to extract table data
            preserve_layout: Whether to preserve spatial layout
            x_tolerance: Horizontal tolerance for text grouping
            y_tolerance: Vertical tolerance for text grouping
        """
        super().__init__("pdfplumber")
        self.extract_tables = extract_tables
        self.preserve_layout = preserve_layout
        self.x_tolerance = x_tolerance
        self.y_tolerance = y_tolerance

    def can_handle(self, file_path: str | Path) -> bool:
        """Check if pdfplumber can handle this file."""
        if not self._validate_pdf(file_path):
            return False

        try:
            with pdfplumber.open(file_path) as pdf:
                # Try to access first page
                if len(pdf.pages) > 0:
                    _ = pdf.pages[0].extract_text()
                return True
        except Exception as e:
            self.logger.debug(
                "pdfplumber_cannot_handle", file_path=str(file_path), error=str(e)
            )
            return False

    async def parse(self, file_path: str | Path) -> PDFParsingResult:
        """Parse PDF using pdfplumber."""
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
                "pdfplumber_parse_error", file_path=str(file_path), error=str(e)
            )
            return PDFParsingResult(
                success=False,
                error=f"PDFPlumber parsing failed: {str(e)}",
                parser_used=self.name,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_sync(self, file_path: str | Path) -> PDFParsingResult:
        """Synchronous PDF parsing with pdfplumber."""
        path = Path(file_path)
        pages = []

        with pdfplumber.open(path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract text with layout preservation
                    if self.preserve_layout:
                        text = page.extract_text(
                            x_tolerance=self.x_tolerance,
                            y_tolerance=self.y_tolerance,
                            layout=True,
                        )
                    else:
                        text = page.extract_text()

                    if text is None:
                        text = ""

                    # Extract detailed text elements with positioning
                    elements = self._extract_text_elements(page)

                    # Extract tables if enabled
                    page_metadata: dict[str, Any] = {
                        "extraction_method": "pdfplumber",
                        "has_positioning": True,
                        "x_tolerance": self.x_tolerance,
                        "y_tolerance": self.y_tolerance,
                    }

                    if self.extract_tables:
                        tables = page.extract_tables()
                        if tables:
                            page_metadata["tables"] = tables
                            page_metadata["table_count"] = len(tables)

                    pdf_page = PDFPage(
                        page_number=page_num + 1,
                        text=text,
                        width=page.width,
                        height=page.height,
                        elements=elements,
                        metadata=page_metadata,
                    )

                    pages.append(pdf_page)

                except Exception as e:
                    self.logger.warning(
                        "pdfplumber_page_error", page_num=page_num + 1, error=str(e)
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
            metadata = {
                "page_count": len(pages),
                "file_size": path.stat().st_size,
                "parser": "pdfplumber",
                "extract_tables": self.extract_tables,
                "preserve_layout": self.preserve_layout,
            }

            # Add PDF metadata if available
            if hasattr(pdf, "metadata") and pdf.metadata:
                metadata.update(
                    {
                        "title": pdf.metadata.get("Title", ""),
                        "author": pdf.metadata.get("Author", ""),
                        "subject": pdf.metadata.get("Subject", ""),
                        "creator": pdf.metadata.get("Creator", ""),
                        "producer": pdf.metadata.get("Producer", ""),
                        "creation_date": str(pdf.metadata.get("CreationDate", "")),
                        "modification_date": str(pdf.metadata.get("ModDate", "")),
                    }
                )

            return PDFParsingResult(success=True, pages=pages, metadata=metadata)

    def _extract_text_elements(self, page) -> list[TextElement]:
        """Extract individual text elements with positioning."""
        elements = []

        try:
            # Get character-level details
            chars = page.chars

            # Group characters into words/elements
            current_word = ""
            current_chars = []

            for char in chars:
                if char.get("text", "").strip():
                    current_word += char["text"]
                    current_chars.append(char)
                else:
                    # End of word, create element
                    if current_word.strip() and current_chars:
                        element = self._create_text_element(current_word, current_chars)
                        if element:
                            elements.append(element)

                    current_word = ""
                    current_chars = []

            # Handle final word
            if current_word.strip() and current_chars:
                element = self._create_text_element(current_word, current_chars)
                if element:
                    elements.append(element)

        except Exception as e:
            self.logger.debug("text_element_extraction_error", error=str(e))

        return elements

    def _create_text_element(self, text: str, chars: list[dict]) -> TextElement | None:
        """Create a TextElement from character data."""
        if not chars:
            return None

        # Calculate bounding box
        x0 = min(char.get("x0", 0) for char in chars)
        y0 = min(char.get("y0", 0) for char in chars)
        x1 = max(char.get("x1", 0) for char in chars)
        y1 = max(char.get("y1", 0) for char in chars)

        # Get font information from first character
        first_char = chars[0]
        font_size = first_char.get("size")
        font_name = first_char.get("fontname", "")

        # Determine formatting
        is_bold = "bold" in font_name.lower() if font_name else False
        is_italic = "italic" in font_name.lower() if font_name else False

        return TextElement(
            text=text,
            bbox=BoundingBox(x0, y0, x1, y1),
            font_size=font_size,
            font_name=font_name,
            is_bold=is_bold,
            is_italic=is_italic,
            confidence=1.0,  # High confidence for direct PDF extraction
        )
