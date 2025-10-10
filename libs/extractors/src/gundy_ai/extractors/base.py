"""Base parser interface for document extraction plugins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from .models import ParsedChunk, ParserManifest


class BaseParser(ABC):
    """Abstract base class for document parsers.

    All parser plugins must implement this interface to be compatible
    with the extraction system. Parsers are responsible for converting
    files into structured text chunks with metadata.

    Example:
        class MyParser(BaseParser):
            @property
            def manifest(self) -> ParserManifest:
                return ParserManifest(
                    name="my_parser",
                    version="1.0.0",
                    supported_types=[".xyz"]
                )

            def parse(self, file_path: str) -> List[ParsedChunk]:
                # Implementation here
                pass
    """

    @property
    @abstractmethod
    def manifest(self) -> ParserManifest:
        """Get parser manifest with metadata and capabilities.

        Returns:
            ParserManifest: Plugin manifest with supported_types, version, etc.
        """
        pass

    @abstractmethod
    def parse(self, file_path: str) -> List[ParsedChunk]:
        """Extract text and metadata from a file.

        Args:
            file_path: Path to the file to parse

        Returns:
            List of ParsedChunk objects containing:
            - text: extracted content
            - span_start: character offset in original
            - span_end: character offset end
            - metadata: dict with parser-specific data

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid or unsupported
            RuntimeError: If parsing fails for other reasons
        """
        pass

    def health_check(self) -> bool:
        """Verify parser dependencies are available.

        Override this method to check for required libraries,
        system tools, or other dependencies.

        Returns:
            True if parser is ready to use, False otherwise
        """
        return True

    def __repr__(self) -> str:
        """String representation of parser."""
        return f"{self.__class__.__name__}(name={self.manifest.name}, version={self.manifest.version})"
