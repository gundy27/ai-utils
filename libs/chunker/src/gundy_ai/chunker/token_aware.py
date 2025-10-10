"""Token-aware text chunker using tiktoken."""

from __future__ import annotations

import time
from typing import List

import structlog
import tiktoken

from .audit import ChunkingEventType, emit_chunking_event
from .base import BaseChunker
from .models import TextChunk

logger = structlog.get_logger(__name__)


class TokenAwareChunker(BaseChunker):
    """Token-aware text chunker that respects LLM token limits.

    Uses tiktoken for accurate token counting to ensure chunks
    never exceed the specified token limit. Ideal for preparing
    text for LLM processing.

    Example:
        chunker = TokenAwareChunker(max_tokens=512, overlap_tokens=50)
        chunks = chunker.chunk("Long text here...")
    """

    def __init__(
        self,
        max_tokens: int = 512,
        overlap_tokens: int = 50,
        encoding_name: str = "cl100k_base",
    ):
        """Initialize token-aware chunker.

        Args:
            max_tokens: Maximum tokens per chunk
            overlap_tokens: Number of tokens to overlap between chunks
            encoding_name: Tiktoken encoding name (cl100k_base for GPT-4/3.5)

        Raises:
            ValueError: If max_tokens <= overlap_tokens
        """
        if overlap_tokens >= max_tokens:
            raise ValueError(
                f"overlap_tokens ({overlap_tokens}) must be less than "
                f"max_tokens ({max_tokens})"
            )

        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.encoding_name = encoding_name

        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.error(
                "encoding_initialization_failed", encoding=encoding_name, error=str(e)
            )
            raise ValueError(f"Invalid encoding name: {encoding_name}") from e

        logger.debug(
            "token_aware_chunker_initialized",
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
            encoding=encoding_name,
        )

    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        """Chunk text using token-aware strategy.

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
            strategy="token_aware",
            input_length=len(text),
            outcome="pending",
            max_tokens=self.max_tokens,
        )

        try:
            # Encode entire text
            tokens = self.encoding.encode(text)
            total_tokens = len(tokens)

            logger.info(
                "chunking_started",
                input_chars=len(text),
                input_tokens=total_tokens,
                max_tokens=self.max_tokens,
                overlap=self.overlap_tokens,
            )

            chunks = []
            start_idx = 0
            chunk_idx = 0

            while start_idx < total_tokens:
                # Determine end index for this chunk
                end_idx = min(start_idx + self.max_tokens, total_tokens)

                # Get tokens for this chunk
                chunk_tokens = tokens[start_idx:end_idx]

                # Decode to text
                chunk_text = self.encoding.decode(chunk_tokens)

                # Calculate character positions (approximate)
                # We decode from the start to get accurate char positions
                if start_idx == 0:
                    char_start = 0
                else:
                    char_start = len(self.encoding.decode(tokens[:start_idx]))

                char_end = len(self.encoding.decode(tokens[:end_idx]))

                # Create chunk
                chunk = TextChunk(
                    chunk_id=f"chunk_{chunk_idx}",
                    text=chunk_text,
                    token_count=len(chunk_tokens),
                    char_count=len(chunk_text),
                    chunk_index=chunk_idx,
                    span_start=char_start,
                    span_end=char_end,
                    metadata={
                        "strategy": "token_aware",
                        "max_tokens": self.max_tokens,
                        "overlap_tokens": self.overlap_tokens,
                        "encoding": self.encoding_name,
                    },
                )

                chunks.append(chunk)
                chunk_idx += 1

                logger.debug(
                    "chunk_created",
                    chunk_id=chunk.chunk_id,
                    tokens=chunk.token_count,
                    chars=chunk.char_count,
                )

                # Move forward, accounting for overlap
                start_idx = end_idx - self.overlap_tokens

                # Prevent infinite loop if we're at the end
                if end_idx >= total_tokens:
                    break

            processing_time_ms = (time.time() - start_time) * 1000
            total_output_tokens = sum(chunk.token_count for chunk in chunks)

            logger.info(
                "chunking_completed",
                chunks_created=len(chunks),
                total_output_tokens=total_output_tokens,
                processing_time_ms=processing_time_ms,
            )

            # Emit completed event
            emit_chunking_event(
                event_type=ChunkingEventType.CHUNKING_COMPLETED,
                strategy="token_aware",
                input_length=len(text),
                outcome="success",
                max_tokens=self.max_tokens,
                input_tokens=total_tokens,
                chunks_created=len(chunks),
                total_output_tokens=total_output_tokens,
                processing_time_ms=processing_time_ms,
            )

            return chunks

        except Exception as e:
            processing_time_ms = (time.time() - start_time) * 1000
            error_msg = f"Chunking failed: {str(e)}"

            logger.error("chunking_failed", error=str(e))

            emit_chunking_event(
                event_type=ChunkingEventType.CHUNKING_FAILED,
                strategy="token_aware",
                input_length=len(text),
                outcome="error",
                max_tokens=self.max_tokens,
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

        tokens = self.encoding.encode(text)
        total_tokens = len(tokens)

        if total_tokens <= self.max_tokens:
            return 1

        # Calculate chunks accounting for overlap
        effective_chunk_size = self.max_tokens - self.overlap_tokens
        estimated = (
            total_tokens - self.overlap_tokens + effective_chunk_size - 1
        ) // effective_chunk_size

        return max(1, estimated)

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TokenAwareChunker(max_tokens={self.max_tokens}, "
            f"overlap={self.overlap_tokens}, encoding={self.encoding_name})"
        )
