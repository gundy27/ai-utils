"""OCR fallback parser for scanned PDFs and images."""

import asyncio
import io
import time
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF for image extraction
import pytesseract
from PIL import Image

from .base import BoundingBox, PDFPage, PDFParser, PDFParsingResult, TextElement


class OCRFallbackParser(PDFParser):
    """OCR-based PDF parser for scanned documents."""

    def __init__(
        self,
        language: str = "eng",
        dpi: int = 300,
        confidence_threshold: float = 0.6,
        preprocess_images: bool = True,
    ):
        """Initialize OCR fallback parser.

        Args:
            language: Tesseract language code (e.g., 'eng', 'spa', 'fra')
            dpi: DPI for image rendering
            confidence_threshold: Minimum confidence for OCR results
            preprocess_images: Whether to preprocess images for better OCR
        """
        super().__init__("ocr_fallback")
        self.language = language
        self.dpi = dpi
        self.confidence_threshold = confidence_threshold
        self.preprocess_images = preprocess_images

    def can_handle(self, file_path: str | Path) -> bool:
        """OCR can handle any valid PDF file."""
        return self._validate_pdf(file_path)

    async def parse(self, file_path: str | Path) -> PDFParsingResult:
        """Parse PDF using OCR."""
        start_time = time.time()

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, self._parse_sync, file_path
            )

            processing_time = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time
            result.parser_used = self.name
            result.ocr_used = True

            return result

        except Exception as e:
            self.logger.error("ocr_parse_error", file_path=str(file_path), error=str(e))
            return PDFParsingResult(
                success=False,
                error=f"OCR parsing failed: {str(e)}",
                parser_used=self.name,
                ocr_used=True,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _parse_sync(self, file_path: str | Path) -> PDFParsingResult:
        """Synchronous OCR parsing."""
        path = Path(file_path)
        pages = []

        doc = fitz.open(str(path))

        try:
            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]

                    # Convert page to image
                    mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)  # Scale for DPI
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")

                    # Convert to PIL Image
                    image = Image.open(io.BytesIO(img_data))

                    # Preprocess image if enabled
                    if self.preprocess_images:
                        image = self._preprocess_image(image)

                    # Perform OCR with detailed data
                    ocr_data = pytesseract.image_to_data(
                        image, lang=self.language, output_type=pytesseract.Output.DICT
                    )

                    # Extract text and elements
                    text, elements = self._process_ocr_data(ocr_data, page.rect)

                    # Page metadata
                    page_metadata: dict[str, Any] = {
                        "extraction_method": "ocr",
                        "has_positioning": True,
                        "ocr_language": self.language,
                        "ocr_dpi": self.dpi,
                        "confidence_threshold": self.confidence_threshold,
                        "preprocessed": self.preprocess_images,
                        "page_rotation": page.rotation,
                    }

                    # Calculate average confidence
                    if elements:
                        avg_confidence = sum(
                            elem.confidence for elem in elements
                        ) / len(elements)
                        page_metadata["average_confidence"] = avg_confidence

                    pdf_page = PDFPage(
                        page_number=page_num + 1,
                        text=text,
                        width=page.rect.width,
                        height=page.rect.height,
                        elements=elements,
                        metadata=page_metadata,
                    )

                    pages.append(pdf_page)

                except Exception as e:
                    self.logger.warning(
                        "ocr_page_error", page_num=page_num + 1, error=str(e)
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
                    "parser": "ocr_fallback",
                    "ocr_language": self.language,
                    "ocr_dpi": self.dpi,
                    "confidence_threshold": self.confidence_threshold,
                    "is_encrypted": doc.needs_pass,
                }
            )

            return PDFParsingResult(success=True, pages=pages, metadata=metadata)

        finally:
            doc.close()

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR results."""
        # Convert to grayscale
        if image.mode != "L":
            image = image.convert("L")

        # Enhance contrast (simple approach)
        # In production, you might want more sophisticated preprocessing
        from PIL import ImageEnhance

        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)

        # Sharpen image
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(2.0)

        return image

    def _process_ocr_data(
        self, ocr_data: dict, page_rect
    ) -> tuple[str, list[TextElement]]:
        """Process OCR data into text and elements."""
        elements = []
        text_parts = []

        # Scale factor from OCR coordinates to PDF coordinates
        scale_x = page_rect.width / max(ocr_data["width"]) if ocr_data["width"] else 1
        scale_y = (
            page_rect.height / max(ocr_data["height"]) if ocr_data["height"] else 1
        )

        for i, text in enumerate(ocr_data["text"]):
            confidence = float(ocr_data["conf"][i]) / 100.0  # Convert to 0-1 range

            # Skip low-confidence or empty text
            if confidence < self.confidence_threshold or not text.strip():
                continue

            # Get bounding box and scale to PDF coordinates
            left = ocr_data["left"][i] * scale_x
            top = ocr_data["top"][i] * scale_y
            width = ocr_data["width"][i] * scale_x
            height = ocr_data["height"][i] * scale_y

            bbox = BoundingBox(x0=left, y0=top, x1=left + width, y1=top + height)

            element = TextElement(text=text, bbox=bbox, confidence=confidence)

            elements.append(element)
            text_parts.append(text)

        # Join text with spaces
        full_text = " ".join(text_parts)

        return full_text, elements
