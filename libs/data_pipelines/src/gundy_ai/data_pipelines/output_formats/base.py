"""Base classes for output formats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog

from ..document import ProcessedDocument

logger = structlog.get_logger(__name__)


class OutputFormat(Enum):
    """Supported output formats."""

    JSON = "json"
    NDJSON = "ndjson"
    PARQUET = "parquet"


@dataclass
class OutputResult:
    """Result of an output operation."""

    success: bool
    output_path: str | Path | None = None
    format: OutputFormat | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    processing_time_ms: float = 0.0

    @property
    def file_size(self) -> int:
        """Get output file size in bytes."""
        if self.output_path and Path(self.output_path).exists():
            return Path(self.output_path).stat().st_size
        return 0


class OutputWriter(ABC):
    """Abstract base class for output writers."""

    def __init__(self, format_type: OutputFormat, **kwargs: Any):
        """Initialize output writer."""
        self.format_type = format_type
        self.config = kwargs
        self.logger = logger.bind(output_format=format_type.value)

    @abstractmethod
    async def write_document(
        self, document: ProcessedDocument, output_path: str | Path, **kwargs: Any
    ) -> OutputResult:
        """Write a single document to the specified path.

        Args:
            document: The processed document to write
            output_path: Path where to write the output
            **kwargs: Additional format-specific options

        Returns:
            OutputResult with operation details
        """
        pass

    @abstractmethod
    async def write_documents(
        self, documents: list[ProcessedDocument], output_path: str | Path, **kwargs: Any
    ) -> OutputResult:
        """Write multiple documents to the specified path.

        Args:
            documents: List of processed documents to write
            output_path: Path where to write the output
            **kwargs: Additional format-specific options

        Returns:
            OutputResult with operation details
        """
        pass

    def _create_result(
        self,
        success: bool,
        output_path: str | Path | None = None,
        error: str | None = None,
        processing_time_ms: float = 0.0,
        **metadata: Any,
    ) -> OutputResult:
        """Create an OutputResult with standard fields."""
        return OutputResult(
            success=success,
            output_path=output_path,
            format=self.format_type,
            error=error,
            processing_time_ms=processing_time_ms,
            metadata={
                "writer": self.__class__.__name__,
                "format": self.format_type.value,
                **metadata,
            },
        )
