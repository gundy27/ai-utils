"""PyMuPDF-based PDF parser for high-performance processing."""

import asyncio
import time
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from .base import BoundingBox, PDFPage, PDFParser, PDFParsingResult, TextElement


class PyMuPDFParser(PDFParser):
    """PDF parser using PyMuPDF (fitz) for high-performance processing."""

    def __init__(
        self,
        extract_images: bool = False,
        extract_links: bool = False,
        preserve_formatting: bool = True,
    ):
        """Initialize PyMuPDF parser.

        Args:
            extract_images: Whether to extract image information
            extract_links: Whether to extract hyperlinks
            preserve_formatting: Whether to preserve text formatting
        """
        super().__init__("pymupdf")
        self.extract_images = extract_images
        self.extract_links = extract_links
        self.preserve_formatting = preserve_formatting

    def can_handle(self, file_path: str | Path) -> bool:
        """Check if PyMuPDF can handle this file."""
        if not self._validate_pdf(file_path):
            return False

        try:
            doc = fitz.open(str(file_path))
            # Try to access first page
            if doc.page_count > 0:
                page = doc[0]
                _ = page.get_text()
            doc.close()
            return True
        except Exception as e:
            self.logger.debug(
                "pymupdf_cannot_handle", file_path=str(file_path), error=str(e)
            )
            return False

    async def parse(self, file_path: str | Path) -> PDFParsingResult:
        """Parse PDF using PyMuPDF."""
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
                "pymupdf_parse_error", file_path=str(file_path), error=str(e)
            )
            return PDFParsingResult(
                success=False,
                error=f"PyMuPDF parsing failed: {str(e)}",
                parser_used=self.name,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_sync(self, file_path: str | Path) -> PDFParsingResult:
        """Synchronous PDF parsing with PyMuPDF."""
        path = Path(file_path)
        pages = []

        doc = fitz.open(str(path))

        try:
            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]

                    # Extract text with formatting if enabled
                    if self.preserve_formatting:
                        text_dict = page.get_text("dict")
                        text = self._extract_formatted_text(text_dict)
                        elements = self._extract_text_elements_from_dict(text_dict)
                    else:
                        text = page.get_text()
                        elements = []

                    # Get page dimensions
                    rect = page.rect
                    width = rect.width
                    height = rect.height

                    # Page metadata
                    page_metadata: dict[str, Any] = {
                        "extraction_method": "pymupdf",
                        "has_positioning": self.preserve_formatting,
                        "page_rotation": page.rotation,
                        "page_rect": [rect.x0, rect.y0, rect.x1, rect.y1],
                    }

                    # Extract images if enabled
                    if self.extract_images:
                        images = page.get_images()
                        if images:
                            page_metadata["images"] = [
                                {
                                    "xref": img[0],
                                    "smask": img[1],
                                    "width": img[2],
                                    "height": img[3],
                                    "bpc": img[4],
                                    "colorspace": img[5],
                                    "alt": img[6],
                                    "name": img[7],
                                    "filter": img[8],
                                }
                                for img in images
                            ]
                            page_metadata["image_count"] = len(images)

                    # Extract links if enabled
                    if self.extract_links:
                        links = page.get_links()
                        if links:
                            page_metadata["links"] = [
                                {
                                    "kind": link.get("kind"),
                                    "from": [
                                        link["from"].x0,
                                        link["from"].y0,
                                        link["from"].x1,
                                        link["from"].y1,
                                    ],
                                    "uri": link.get("uri", ""),
                                    "page": link.get("page", -1),
                                }
                                for link in links
                            ]
                            page_metadata["link_count"] = len(links)

                    pdf_page = PDFPage(
                        page_number=page_num + 1,
                        text=text,
                        width=width,
                        height=height,
                        elements=elements,
                        metadata=page_metadata,
                    )

                    pages.append(pdf_page)

                except Exception as e:
                    self.logger.warning(
                        "pymupdf_page_error", page_num=page_num + 1, error=str(e)
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
            metadata = doc.metadata.copy() if doc.metadata else {}
            metadata.update(
                {
                    "page_count": doc.page_count,
                    "file_size": path.stat().st_size,
                    "parser": "pymupdf",
                    "is_pdf": doc.is_pdf,
                    "is_encrypted": doc.needs_pass,
                    "extract_images": self.extract_images,
                    "extract_links": self.extract_links,
                    "preserve_formatting": self.preserve_formatting,
                }
            )

            return PDFParsingResult(success=True, pages=pages, metadata=metadata)

        finally:
            doc.close()

    def _extract_formatted_text(self, text_dict: dict) -> str:
        """Extract text from PyMuPDF text dictionary while preserving structure."""
        text_parts = []

        for block in text_dict.get("blocks", []):
            if "lines" in block:  # Text block
                block_text = []
                for line in block["lines"]:
                    line_text = []
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        if span_text.strip():
                            line_text.append(span_text)
                    if line_text:
                        block_text.append(" ".join(line_text))

                if block_text:
                    text_parts.append("\n".join(block_text))

        return "\n\n".join(text_parts)

    def _extract_text_elements_from_dict(self, text_dict: dict) -> list[TextElement]:
        """Extract TextElements from PyMuPDF text dictionary."""
        elements = []

        for block in text_dict.get("blocks", []):
            if "lines" in block:  # Text block
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue

                        # Get bounding box
                        bbox_data = span.get("bbox", [0, 0, 0, 0])
                        bbox = BoundingBox(
                            x0=bbox_data[0],
                            y0=bbox_data[1],
                            x1=bbox_data[2],
                            y1=bbox_data[3],
                        )

                        # Get font information
                        font_size = span.get("size", 0)
                        font_name = span.get("font", "")
                        flags = span.get("flags", 0)

                        # Decode font flags (PyMuPDF specific)
                        is_bold = bool(flags & 2**4)  # Bold flag
                        is_italic = bool(flags & 2**1)  # Italic flag

                        element = TextElement(
                            text=text,
                            bbox=bbox,
                            font_size=font_size,
                            font_name=font_name,
                            is_bold=is_bold,
                            is_italic=is_italic,
                            confidence=1.0,  # High confidence for direct PDF extraction
                        )

                        elements.append(element)

        return elements
