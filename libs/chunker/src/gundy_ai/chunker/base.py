"""Base chunker interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from .models import TextChunk


class BaseChunker(ABC):
    """Abstract base class for text chunkers.

    All chunker implementations must implement this interface.
    Chunkers are responsible for splitting text into manageable pieces
    with configurable overlap and size constraints.

    Example:
        class MyChunker(BaseChunker):
            def chunk(self, text: str) -> List[TextChunk]:
                # Implementation here
                pass
    """

    @abstractmethod
    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        """Chunk text into smaller pieces.

        Args:
            text: Text to chunk
            **kwargs: Additional chunker-specific arguments

        Returns:
            List of TextChunk objects with:
            - chunk_id: Unique identifier
            - text: Chunk content
            - token_count: Number of tokens
            - char_count: Number of characters
            - chunk_index: Position in sequence
            - span_start/span_end: Offsets in original text
            - metadata: Chunker-specific metadata

        Raises:
            ValueError: If text is invalid or parameters are invalid
        """
        pass

    @abstractmethod
    def estimate_chunks(self, text: str) -> int:
        """Estimate number of chunks that will be created.

        Useful for progress tracking and resource planning.

        Args:
            text: Text to estimate

        Returns:
            Estimated number of chunks
        """
        pass

    def __repr__(self) -> str:
        """String representation of chunker."""
        return f"{self.__class__.__name__}()"
