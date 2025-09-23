"""Base classes for text cleaning."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class CleaningResult:
    """Result of a text cleaning operation."""

    success: bool
    cleaned_text: str = ""
    original_length: int = 0
    cleaned_length: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    processing_time_ms: float = 0.0

    @property
    def reduction_ratio(self) -> float:
        """Calculate text reduction ratio."""
        if self.original_length == 0:
            return 0.0
        return (self.original_length - self.cleaned_length) / self.original_length

    @property
    def characters_removed(self) -> int:
        """Get number of characters removed."""
        return self.original_length - self.cleaned_length


class TextCleaner(ABC):
    """Abstract base class for text cleaners."""

    def __init__(self, name: str, **kwargs: Any):
        """Initialize text cleaner with name and configuration."""
        self.name = name
        self.config = kwargs
        self.logger = logger.bind(cleaner=name)

    @abstractmethod
    async def clean(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> CleaningResult:
        """Clean the input text.

        Args:
            text: The text to clean
            metadata: Optional metadata about the text source

        Returns:
            CleaningResult with cleaned text and statistics
        """
        pass

    def _create_result(
        self,
        success: bool,
        cleaned_text: str = "",
        original_text: str = "",
        error: str | None = None,
        processing_time_ms: float = 0.0,
        **metadata: Any,
    ) -> CleaningResult:
        """Create a CleaningResult with standard fields."""
        return CleaningResult(
            success=success,
            cleaned_text=cleaned_text,
            original_length=len(original_text),
            cleaned_length=len(cleaned_text),
            error=error,
            processing_time_ms=processing_time_ms,
            metadata={"cleaner": self.name, **metadata},
        )
