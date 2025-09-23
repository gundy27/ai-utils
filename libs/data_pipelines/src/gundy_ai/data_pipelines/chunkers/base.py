"""Base classes for advanced text chunking."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import structlog

from ..document import ProcessedDocument, TextChunk

logger = structlog.get_logger(__name__)


@dataclass
class ChunkingResult:
    """Result of a chunking operation."""

    success: bool
    chunks: list[TextChunk] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    processing_time_ms: float = 0.0

    @property
    def chunk_count(self) -> int:
        """Get total number of chunks."""
        return len(self.chunks)

    @property
    def total_tokens(self) -> int:
        """Get total token count across all chunks."""
        return sum(chunk.token_count for chunk in self.chunks)


class BaseChunker(ABC):
    """Abstract base class for text chunkers."""

    def __init__(self, name: str, **kwargs: Any):
        """Initialize chunker with name and configuration."""
        self.name = name
        self.config = kwargs
        self.logger = logger.bind(chunker=name)

    @abstractmethod
    async def chunk(self, document: ProcessedDocument) -> ChunkingResult:
        """Chunk the document text.

        Args:
            document: The processed document to chunk

        Returns:
            ChunkingResult with generated chunks
        """
        pass

    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        start_char: int,
        end_char: int,
        token_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> TextChunk:
        """Create a TextChunk with standard metadata."""
        chunk_metadata = {
            "chunker": self.name,
            "chunking_strategy": self.name,
            **(metadata or {}),
        }

        return TextChunk(
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            token_count=token_count,
            metadata=chunk_metadata,
        )
