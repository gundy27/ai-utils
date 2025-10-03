"""Token-aware chunking strategies for LLM compatibility."""

import time
from typing import Any, List

import tiktoken
import structlog

from ..document import ProcessedDocument, TextChunk
from .base import BaseChunker, ChunkingResult

logger = structlog.get_logger(__name__)


class TokenAwareChunker(BaseChunker):
    """Chunker that ensures chunks stay within token limits."""

    def __init__(
        self,
        max_tokens: int = 8192,
        target_tokens: int = 4000,
        overlap_tokens: int = 200,
        encoding_name: str = "cl100k_base",  # GPT-4/GPT-3.5-turbo encoding
        preserve_sentences: bool = True,
        preserve_paragraphs: bool = True,
    ):
        """Initialize token-aware chunker.

        Args:
            max_tokens: Maximum tokens per chunk (hard limit)
            target_tokens: Target tokens per chunk (soft limit)
            overlap_tokens: Overlap between chunks in tokens
            encoding_name: Tiktoken encoding name
            preserve_sentences: Try to preserve sentence boundaries
            preserve_paragraphs: Try to preserve paragraph boundaries
        """
        super().__init__("token_aware")
        self.max_tokens = max_tokens
        self.target_tokens = target_tokens
        self.overlap_tokens = overlap_tokens
        self.preserve_sentences = preserve_sentences
        self.preserve_paragraphs = preserve_paragraphs

        try:
            self.encoding = tiktoken.get_encoding(encoding_name)
        except Exception as e:
            logger.warning(
                "failed_to_load_encoding", encoding=encoding_name, error=str(e)
            )
            # Fallback to a basic token counter
            self.encoding = None

        self.logger = logger.bind(chunker="token_aware")

    async def chunk(self, document: ProcessedDocument) -> ChunkingResult:
        """Chunk document with token awareness."""
        start_time = time.time()

        try:
            # If document already has chunks, split oversized ones
            if document.chunks:
                chunks = await self._split_oversized_chunks(document.chunks)
            else:
                # Create initial chunks from full text
                chunks = await self._create_token_aware_chunks(document.full_text)

            processing_time = (time.time() - start_time) * 1000

            # Calculate statistics
            token_counts = [self._count_tokens(chunk.content) for chunk in chunks]
            avg_tokens = sum(token_counts) / len(token_counts) if token_counts else 0
            max_chunk_tokens = max(token_counts) if token_counts else 0

            self.logger.info(
                "token_aware_chunking_complete",
                chunk_count=len(chunks),
                avg_tokens=avg_tokens,
                max_tokens=max_chunk_tokens,
                processing_time_ms=processing_time,
            )

            return ChunkingResult(
                success=True,
                chunks=chunks,
                processing_time_ms=processing_time,
                metadata={
                    "chunker": self.name,
                    "strategy": "token_aware",
                    "max_tokens_limit": self.max_tokens,
                    "target_tokens": self.target_tokens,
                    "avg_tokens_per_chunk": avg_tokens,
                    "max_tokens_in_chunk": max_chunk_tokens,
                    "chunks_split": sum(
                        1 for chunk in chunks if "split_from" in chunk.metadata
                    ),
                    "encoding": self.encoding.name if self.encoding else "fallback",
                },
            )

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self.logger.error("token_aware_chunking_error", error=str(e))

            return ChunkingResult(
                success=False,
                chunks=[],
                processing_time_ms=processing_time,
                error=f"Token-aware chunking failed: {str(e)}",
            )

    async def _split_oversized_chunks(self, chunks: List[TextChunk]) -> List[TextChunk]:
        """Split chunks that exceed token limits."""
        result_chunks = []

        for chunk in chunks:
            token_count = self._count_tokens(chunk.content)

            if token_count <= self.max_tokens:
                # Chunk is within limits
                result_chunks.append(chunk)
            else:
                # Split oversized chunk
                self.logger.info(
                    "splitting_oversized_chunk",
                    original_tokens=token_count,
                    chunk_index=chunk.chunk_index,
                    max_tokens=self.max_tokens,
                )

                split_chunks = await self._split_single_chunk(chunk)
                result_chunks.extend(split_chunks)

        # Reindex chunks
        for i, chunk in enumerate(result_chunks):
            chunk.chunk_index = i

        return result_chunks

    async def _split_single_chunk(self, chunk: TextChunk) -> List[TextChunk]:
        """Split a single oversized chunk into smaller chunks."""
        content = chunk.content
        split_chunks = []

        # Try different splitting strategies in order of preference
        if self.preserve_paragraphs:
            split_chunks = self._split_by_paragraphs(content)

        if not split_chunks or any(
            self._count_tokens(c) > self.max_tokens for c in split_chunks
        ):
            if self.preserve_sentences:
                split_chunks = self._split_by_sentences(content)

        if not split_chunks or any(
            self._count_tokens(c) > self.max_tokens for c in split_chunks
        ):
            # Fallback to character-based splitting
            split_chunks = self._split_by_characters(content)

        # Convert to TextChunk objects
        result_chunks = []
        current_char_offset = chunk.start_char

        for i, split_content in enumerate(split_chunks):
            if not split_content.strip():
                continue

            # Calculate character positions
            start_char = current_char_offset
            end_char = start_char + len(split_content)
            current_char_offset = end_char

            # Create new chunk
            new_chunk = TextChunk(
                content=split_content,
                chunk_index=chunk.chunk_index + i,  # Will be reindexed later
                start_char=start_char,
                end_char=end_char,
                token_count=self._count_tokens(split_content),
                metadata={
                    **chunk.metadata,
                    "split_from": chunk.chunk_index,
                    "split_part": i + 1,
                    "split_total": len(split_chunks),
                    "split_strategy": "token_aware",
                },
            )

            result_chunks.append(new_chunk)

        return result_chunks

    async def _create_token_aware_chunks(self, text: str) -> List[TextChunk]:
        """Create chunks from full text with token awareness."""
        chunks = []
        current_pos = 0
        chunk_index = 0

        while current_pos < len(text):
            # Find the end position for this chunk
            end_pos = self._find_chunk_end(text, current_pos)

            # Extract chunk content
            chunk_content = text[current_pos:end_pos].strip()

            if chunk_content:
                chunk = TextChunk(
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_char=current_pos,
                    end_char=end_pos,
                    token_count=self._count_tokens(chunk_content),
                    metadata={
                        "chunker": self.name,
                        "strategy": "token_aware",
                        "created_from_full_text": True,
                    },
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move to next chunk with overlap
            overlap_chars = self._tokens_to_approximate_chars(self.overlap_tokens)
            current_pos = max(current_pos + 1, end_pos - overlap_chars)

        return chunks

    def _find_chunk_end(self, text: str, start_pos: int) -> int:
        """Find the optimal end position for a chunk."""
        # Start with target token count
        target_chars = self._tokens_to_approximate_chars(self.target_tokens)
        # max_chars = self._tokens_to_approximate_chars(self.max_tokens)  # Unused for now

        # Initial end position
        end_pos = min(start_pos + target_chars, len(text))

        # Adjust based on actual token count
        chunk_text = text[start_pos:end_pos]
        token_count = self._count_tokens(chunk_text)

        # If we're under target, try to expand
        while token_count < self.target_tokens and end_pos < len(text):
            # Try to expand by 10% more characters
            new_end = min(end_pos + max(100, target_chars // 10), len(text))
            new_chunk_text = text[start_pos:new_end]
            new_token_count = self._count_tokens(new_chunk_text)

            if new_token_count > self.max_tokens:
                break

            end_pos = new_end
            token_count = new_token_count

        # If we're over max, shrink
        while token_count > self.max_tokens and end_pos > start_pos + 100:
            # Shrink by 10%
            end_pos = max(start_pos + 100, end_pos - max(100, target_chars // 10))
            chunk_text = text[start_pos:end_pos]
            token_count = self._count_tokens(chunk_text)

        # Try to end at natural boundaries
        if self.preserve_paragraphs:
            boundary_pos = self._find_paragraph_boundary(text, end_pos, start_pos)
            if boundary_pos > start_pos:
                end_pos = boundary_pos
        elif self.preserve_sentences:
            boundary_pos = self._find_sentence_boundary(text, end_pos, start_pos)
            if boundary_pos > start_pos:
                end_pos = boundary_pos

        return min(end_pos, len(text))

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Split text by paragraphs, respecting token limits."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            # Check if adding this paragraph would exceed limits
            test_chunk = current_chunk + ("\n\n" if current_chunk else "") + paragraph

            if self._count_tokens(test_chunk) <= self.max_tokens:
                current_chunk = test_chunk
            else:
                # Save current chunk if it has content
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                # Start new chunk with current paragraph
                if self._count_tokens(paragraph) <= self.max_tokens:
                    current_chunk = paragraph
                else:
                    # Paragraph itself is too large, split by sentences
                    sentence_chunks = self._split_by_sentences(paragraph)
                    chunks.extend(sentence_chunks[:-1])  # Add all but last
                    current_chunk = sentence_chunks[-1] if sentence_chunks else ""

        # Add final chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text by sentences, respecting token limits."""
        import re

        # Simple sentence splitting (can be enhanced with nltk/spacy)
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            test_chunk = current_chunk + (" " if current_chunk else "") + sentence

            if self._count_tokens(test_chunk) <= self.max_tokens:
                current_chunk = test_chunk
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())

                if self._count_tokens(sentence) <= self.max_tokens:
                    current_chunk = sentence
                else:
                    # Sentence is too large, split by characters
                    char_chunks = self._split_by_characters(sentence)
                    chunks.extend(char_chunks[:-1])
                    current_chunk = char_chunks[-1] if char_chunks else ""

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _split_by_characters(self, text: str) -> List[str]:
        """Split text by characters as last resort."""
        chunks = []
        current_pos = 0

        while current_pos < len(text):
            # Binary search for maximum chunk size
            left, right = (
                current_pos + 1,
                min(current_pos + self.max_tokens * 4, len(text)),
            )
            best_end = current_pos + 1

            while left <= right:
                mid = (left + right) // 2
                chunk_text = text[current_pos:mid]

                if self._count_tokens(chunk_text) <= self.max_tokens:
                    best_end = mid
                    left = mid + 1
                else:
                    right = mid - 1

            chunk_text = text[current_pos:best_end].strip()
            if chunk_text:
                chunks.append(chunk_text)

            current_pos = best_end

        return chunks

    def _find_paragraph_boundary(self, text: str, pos: int, min_pos: int) -> int:
        """Find nearest paragraph boundary before pos."""
        # Look backwards for paragraph break
        for i in range(pos, min_pos, -1):
            if i < len(text) - 1 and text[i : i + 2] == "\n\n":
                return i
        return pos

    def _find_sentence_boundary(self, text: str, pos: int, min_pos: int) -> int:
        """Find nearest sentence boundary before pos."""
        # Look backwards for sentence ending
        for i in range(pos, min_pos, -1):
            if i < len(text) and text[i] in ".!?":
                # Make sure it's followed by whitespace or end of text
                if i + 1 >= len(text) or text[i + 1].isspace():
                    return i + 1
        return pos

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if not text:
            return 0

        if self.encoding:
            try:
                return len(self.encoding.encode(text))
            except Exception:
                pass

        # Fallback: approximate token count (1 token ≈ 4 characters for English)
        return max(1, len(text) // 4)

    def _tokens_to_approximate_chars(self, tokens: int) -> int:
        """Convert token count to approximate character count."""
        return tokens * 4  # Rough approximation for English text


class ChunkSplittingFilter:
    """Filter to split oversized chunks in existing documents."""

    def __init__(
        self,
        max_tokens: int | None = None,
        target_tokens: int | None = None,
        overlap_tokens: int | None = None,
        encoding_name: str | None = None,
        chunking_config: Any | None = None,
    ):
        """Initialize chunk splitting filter.

        Args:
            max_tokens: Maximum tokens per chunk (None to use global config)
            target_tokens: Target tokens per chunk (None to use global config)
            overlap_tokens: Overlap between split chunks (None to use global config)
            encoding_name: Tiktoken encoding name (None to use global config)
            chunking_config: Custom chunking configuration (None to use global config)
        """
        # Import here to avoid circular imports
        from ..config import get_config

        if chunking_config is None:
            chunking_config = get_config().chunking

        self.chunker = TokenAwareChunker(
            max_tokens=max_tokens or chunking_config.max_tokens,
            target_tokens=target_tokens or chunking_config.target_tokens,
            overlap_tokens=overlap_tokens or chunking_config.overlap_tokens,
            encoding_name=encoding_name or chunking_config.encoding_name,
            preserve_sentences=chunking_config.preserve_sentences,
            preserve_paragraphs=chunking_config.preserve_paragraphs,
        )

    async def filter_document(self, document: ProcessedDocument) -> ProcessedDocument:
        """Filter document to split oversized chunks."""
        if not document.chunks:
            return document

        # Check if any chunks exceed limits
        oversized_chunks = [
            chunk
            for chunk in document.chunks
            if self.chunker._count_tokens(chunk.content) > self.chunker.max_tokens
        ]

        if not oversized_chunks:
            # No oversized chunks, return as-is
            return document

        # Split oversized chunks
        result = await self.chunker.chunk(document)

        if result.success:
            # Update document with split chunks
            document.chunks = result.chunks

            # Update metadata
            document.metadata.custom_metadata.update(
                {
                    "chunk_splitting_applied": True,
                    "original_chunk_count": len(document.chunks)
                    - len(result.chunks)
                    + len(oversized_chunks),
                    "final_chunk_count": len(result.chunks),
                    "chunks_split": len(oversized_chunks),
                    **result.metadata,
                }
            )

        return document

    async def filter_documents(
        self, documents: List[ProcessedDocument]
    ) -> List[ProcessedDocument]:
        """Filter multiple documents to split oversized chunks."""
        filtered_docs = []

        for document in documents:
            filtered_doc = await self.filter_document(document)
            filtered_docs.append(filtered_doc)

        return filtered_docs
