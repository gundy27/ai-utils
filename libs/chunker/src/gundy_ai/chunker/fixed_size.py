"""Fixed-size character-based text chunker."""

from __future__ import annotations

import time
from typing import List

import structlog

from .audit import ChunkingEventType, emit_chunking_event
from .base import BaseChunker
from .models import TextChunk

logger = structlog.get_logger(__name__)


class FixedSizeChunker(BaseChunker):
    """Fixed-size character-based text chunker.

    Simpler alternative to token-aware chunking when token limits
    are not a concern. Splits text based on character count with overlap.

    Example:
        chunker = FixedSizeChunker(chunk_size=1000, overlap_size=100)
        chunks = chunker.chunk("Long text here...")
    """

    def __init__(self, chunk_size: int = 1000, overlap_size: int = 100):
        """Initialize fixed-size chunker.

        Args:
            chunk_size: Maximum characters per chunk
            overlap_size: Number of characters to overlap between chunks

        Raises:
            ValueError: If chunk_size <= overlap_size
        """
        if overlap_size >= chunk_size:
            raise ValueError(
                f"overlap_size ({overlap_size}) must be less than "
                f"chunk_size ({chunk_size})"
            )

        self.chunk_size = chunk_size
        self.overlap_size = overlap_size

        logger.debug(
            "fixed_size_chunker_initialized",
            chunk_size=chunk_size,
            overlap_size=overlap_size,
        )

    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        """Chunk text using fixed-size strategy.

        Args:
            text: Text to chunk
            **kwargs: Additional arguments (ignored)

        Returns:
            List of TextChunk objects

        Raises:
            ValueError: If text is empty
        """
        start_time = time.time()

        if not text:
            logger.warning("empty_text_provided")
            return []

        # Emit started event
        emit_chunking_event(
            event_type=ChunkingEventType.CHUNKING_STARTED,
            strategy="fixed_size",
            input_length=len(text),
            outcome="pending",
            chunk_size=self.chunk_size,
        )

        try:
            logger.info(
                "chunking_started",
                input_chars=len(text),
                chunk_size=self.chunk_size,
                overlap=self.overlap_size,
            )

            chunks = []
            start_pos = 0
            chunk_idx = 0

            while start_pos < len(text):
                # Determine end position for this chunk
                end_pos = min(start_pos + self.chunk_size, len(text))

                # Extract chunk text
                chunk_text = text[start_pos:end_pos]

                # Create chunk (token_count = 0 for fixed-size strategy)
                chunk = TextChunk(
                    chunk_id=f"chunk_{chunk_idx}",
                    text=chunk_text,
                    token_count=0,  # Not calculated for fixed-size
                    char_count=len(chunk_text),
                    chunk_index=chunk_idx,
                    span_start=start_pos,
                    span_end=end_pos,
                    metadata={
                        "strategy": "fixed_size",
                        "chunk_size": self.chunk_size,
                        "overlap_size": self.overlap_size,
                    },
                )

                chunks.append(chunk)
                chunk_idx += 1

                logger.debug(
                    "chunk_created", chunk_id=chunk.chunk_id, chars=chunk.char_count
                )

                # Move forward, accounting for overlap
                start_pos = end_pos - self.overlap_size

                # Prevent infinite loop if we're at the end
                if end_pos >= len(text):
                    break

            processing_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "chunking_completed",
                chunks_created=len(chunks),
                processing_time_ms=processing_time_ms,
            )

            # Emit completed event
            emit_chunking_event(
                event_type=ChunkingEventType.CHUNKING_COMPLETED,
                strategy="fixed_size",
                input_length=len(text),
                outcome="success",
                chunk_size=self.chunk_size,
                chunks_created=len(chunks),
                processing_time_ms=processing_time_ms,
            )

            return chunks

        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Chunking failed: {str(e)}"

            logger.error("chunking_failed", error=str(e))

            emit_chunking_event(
                event_type=ChunkingEventType.CHUNKING_FAILED,
                strategy="fixed_size",
                input_length=len(text),
                outcome="error",
                chunk_size=self.chunk_size,
                processing_time_ms=processing_time_ms,
                error_message=error_msg,
            )

            raise RuntimeError(error_msg) from e

    def estimate_chunks(self, text: str) -> int:
        """Estimate number of chunks for given text.

        Args:
            text: Text to estimate

        Returns:
            Estimated number of chunks
        """
        if not text:
            return 0

        if len(text) <= self.chunk_size:
            return 1

        # Calculate chunks accounting for overlap
        effective_chunk_size = self.chunk_size - self.overlap_size
        estimated = (
            len(text) - self.overlap_size + effective_chunk_size - 1
        ) // effective_chunk_size

        return max(1, estimated)

    def __repr__(self) -> str:
        """String representation."""
        return f"FixedSizeChunker(chunk_size={self.chunk_size}, overlap={self.overlap_size})"
