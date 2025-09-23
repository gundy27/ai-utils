"""Base classes for PDF parsing."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class BoundingBox:
    """Bounding box for text elements."""

    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        """Get width of bounding box."""
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        """Get height of bounding box."""
        return self.y1 - self.y0


@dataclass
class TextElement:
    """A text element with position and formatting information."""

    text: str
    bbox: BoundingBox
    font_size: float | None = None
    font_name: str | None = None
    is_bold: bool = False
    is_italic: bool = False
    confidence: float = 1.0  # OCR confidence score


@dataclass
class PDFPage:
    """A single page from a PDF with extracted content."""

    page_number: int
    text: str
    width: float
    height: float
    elements: list[TextElement] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_text_by_region(self, bbox: BoundingBox) -> str:
        """Extract text from a specific region of the page."""
        region_elements = [
            elem for elem in self.elements if self._bbox_overlaps(elem.bbox, bbox)
        ]
        return " ".join(elem.text for elem in region_elements)

    def _bbox_overlaps(self, bbox1: BoundingBox, bbox2: BoundingBox) -> bool:
        """Check if two bounding boxes overlap."""
        return not (
            bbox1.x1 < bbox2.x0
            or bbox2.x1 < bbox1.x0
            or bbox1.y1 < bbox2.y0
            or bbox2.y1 < bbox1.y0
        )


@dataclass
class PDFParsingResult:
    """Result of PDF parsing operation."""

    success: bool
    pages: list[PDFPage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    parser_used: str | None = None
    ocr_used: bool = False
    processing_time_ms: float = 0.0

    @property
    def page_count(self) -> int:
        """Get total number of pages."""
        return len(self.pages)

    @property
    def total_text_length(self) -> int:
        """Get total character count across all pages."""
        return sum(len(page.text) for page in self.pages)

    def get_full_text(self) -> str:
        """Get concatenated text from all pages."""
        return "\n\n".join(page.text for page in self.pages)


class PDFParser(ABC):
    """Abstract base class for PDF parsers."""

    def __init__(self, name: str):
        """Initialize parser with name."""
        self.name = name
        self.logger = logger.bind(parser=name)

    @abstractmethod
    async def parse(self, file_path: str | Path) -> PDFParsingResult:
        """Parse a PDF file and extract text and metadata.

        Args:
            file_path: Path to the PDF file

        Returns:
            PDFParsingResult with extracted content
        """
        pass

    @abstractmethod
    def can_handle(self, file_path: str | Path) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to the PDF file

        Returns:
            True if parser can handle the file
        """
        pass

    def _validate_pdf(self, file_path: str | Path) -> bool:
        """Validate that the file is a PDF."""
        path = Path(file_path)
        if not path.exists():
            return False
        if not path.is_file():
            return False
        if path.suffix.lower() != ".pdf":
            return False

        # Check PDF magic bytes
        try:
            with open(path, "rb") as f:
                header = f.read(4)
                return header == b"%PDF"
        except Exception:
            return False
