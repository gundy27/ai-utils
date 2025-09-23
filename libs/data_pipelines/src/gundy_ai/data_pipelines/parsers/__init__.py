"""PDF parsing utilities with multiple backend support."""

from .base import PDFParser, PDFParsingResult, PDFPage
from .pdfplumber_parser import PDFPlumberParser
from .pymupdf_parser import PyMuPDFParser
from .pypdf_parser import PyPDFParser
from .ocr_fallback import OCRFallbackParser

__all__ = [
    "PDFParser",
    "PDFParsingResult",
    "PDFPage",
    "PDFPlumberParser",
    "PyMuPDFParser",
    "PyPDFParser",
    "OCRFallbackParser",
]
