"""Document extraction plugins for AI applications."""

from .audit import ExtractionAuditEvent, ExtractionEventType, emit_extraction_event
from .base import BaseParser
from .models import ParsedChunk, ParserManifest
from .registry import ParserRegistry

__version__ = "0.1.0"

__all__ = [
    "BaseParser",
    "ParsedChunk",
    "ParserManifest",
    "ParserRegistry",
    "ExtractionAuditEvent",
    "ExtractionEventType",
    "emit_extraction_event",
]

# Import parsers conditionally (may fail if dependencies not installed)
# Using importlib.util.find_spec to check availability without importing
from importlib.util import find_spec

if find_spec("gundy_ai.extractors.parsers.txt") is not None:
    try:
        from .parsers import TXTParser  # noqa: F401

        __all__.append("TXTParser")
    except ImportError:
        pass

if find_spec("pypdf") is not None:
    try:
        from .parsers import PDFParser  # noqa: F401

        __all__.append("PDFParser")
    except ImportError:
        pass

if find_spec("docx") is not None:
    try:
        from .parsers import DOCXParser  # noqa: F401

        __all__.append("DOCXParser")
    except ImportError:
        pass

if find_spec("bs4") is not None and find_spec("httpx") is not None:
    try:
        from .parsers import HTMLParser  # noqa: F401

        __all__.append("HTMLParser")
    except ImportError:
        pass
