"""Semantic chunking using embedding-based similarity."""

import asyncio
import time
from typing import Any

import numpy as np
import tiktoken
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from ..document import ProcessedDocument, TextChunk
from .base import BaseChunker, ChunkingResult


class SemanticChunker(BaseChunker):
    """Chunker that uses semantic similarity to create coherent chunks."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        max_chunk_size: int = 1000,
        min_chunk_size: int = 100,
        similarity_threshold: float = 0.7,
        sentence_window: int = 3,
        overlap_sentences: int = 1,
        **kwargs: Any,
    ):
        """Initialize semantic chunker.

        Args:
            model_name: Sentence transformer model name
            max_chunk_size: Maximum tokens per chunk
            min_chunk_size: Minimum tokens per chunk
            similarity_threshold: Similarity threshold for merging sentences
            sentence_window: Number of sentences to consider for similarity
            overlap_sentences: Number of sentences to overlap between chunks
        """
        super().__init__("semantic", **kwargs)

        self.model_name = model_name
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.similarity_threshold = similarity_threshold
        self.sentence_window = sentence_window
        self.overlap_sentences = overlap_sentences

        # Initialize models
        self.sentence_model: SentenceTransformer | None = None
        self.encoding = tiktoken.get_encoding("cl100k_base")

    async def chunk(self, document: ProcessedDocument) -> ChunkingResult:
        """Chunk document using semantic similarity."""
        start_time = time.time()

        try:
            # Initialize sentence transformer if needed
            if self.sentence_model is None:
                self.logger.info("loading_sentence_transformer", model=self.model_name)
                self.sentence_model = await asyncio.get_event_loop().run_in_executor(
                    None, SentenceTransformer, self.model_name
                )

            # Split text into sentences
            sentences = await self._split_into_sentences(document.full_text)

            if not sentences:
                return ChunkingResult(
                    success=False, error="No sentences found in document"
                )

            # Generate embeddings for sentences
            embeddings = await self._generate_sentence_embeddings(sentences)

            # Group sentences into semantic chunks
            chunks = await self._create_semantic_chunks(
                sentences, embeddings, document.full_text
            )

            processing_time = (time.time() - start_time) * 1000

            return ChunkingResult(
                success=True,
                chunks=chunks,
                metadata={
                    "sentence_count": len(sentences),
                    "model_name": self.model_name,
                    "similarity_threshold": self.similarity_threshold,
                    "max_chunk_size": self.max_chunk_size,
                    "min_chunk_size": self.min_chunk_size,
                    "sentence_window": self.sentence_window,
                    "overlap_sentences": self.overlap_sentences,
                },
                processing_time_ms=processing_time,
            )

        except Exception as e:
            self.logger.error("semantic_chunking_error", error=str(e))
            return ChunkingResult(
                success=False,
                error=f"Semantic chunking failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        # Simple sentence splitting - could be enhanced with spaCy or NLTK
        import re

        # Split on sentence endings, but be careful with abbreviations
        sentences = re.split(r"(?<=[.!?])\s+", text)

        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Filter very short sentences
                cleaned_sentences.append(sentence)

        return cleaned_sentences

    async def _generate_sentence_embeddings(self, sentences: list[str]) -> np.ndarray:
        """Generate embeddings for sentences."""
        if not self.sentence_model:
            raise ValueError("Sentence model not initialized")

        # Generate embeddings in executor to avoid blocking
        embeddings = await asyncio.get_event_loop().run_in_executor(
            None, self.sentence_model.encode, sentences
        )

        return embeddings

    async def _create_semantic_chunks(
        self, sentences: list[str], embeddings: np.ndarray, full_text: str
    ) -> list[TextChunk]:
        """Create chunks based on semantic similarity."""
        if len(sentences) == 0:
            return []

        chunks = []
        current_chunk_sentences = []
        current_chunk_indices = []
        chunk_index = 0

        i = 0
        while i < len(sentences):
            # Start new chunk with current sentence
            if not current_chunk_sentences:
                current_chunk_sentences = [sentences[i]]
                current_chunk_indices = [i]
                i += 1
                continue

            # Check if we can add more sentences to current chunk
            can_add_more = True

            while can_add_more and i < len(sentences):
                # Calculate similarity with recent sentences in chunk
                window_start = max(
                    0, len(current_chunk_sentences) - self.sentence_window
                )
                chunk_window_embeddings = embeddings[
                    current_chunk_indices[window_start:]
                ]
                candidate_embedding = embeddings[i : i + 1]

                # Calculate average similarity
                similarities = cosine_similarity(
                    candidate_embedding, chunk_window_embeddings
                )[0]
                avg_similarity = np.mean(similarities)

                # Check token count if we add this sentence
                test_chunk_text = " ".join(current_chunk_sentences + [sentences[i]])
                test_token_count = len(self.encoding.encode(test_chunk_text))

                # Decide whether to add sentence to current chunk
                if (
                    avg_similarity >= self.similarity_threshold
                    and test_token_count <= self.max_chunk_size
                ):
                    current_chunk_sentences.append(sentences[i])
                    current_chunk_indices.append(i)
                    i += 1
                else:
                    can_add_more = False

            # Create chunk from current sentences
            chunk_text = " ".join(current_chunk_sentences)
            token_count = len(self.encoding.encode(chunk_text))

            # Find character positions in full text
            start_char = full_text.find(current_chunk_sentences[0])
            if start_char == -1:
                start_char = 0

            end_char = start_char + len(chunk_text)

            # Create chunk
            chunk = self._create_chunk(
                content=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=end_char,
                token_count=token_count,
                metadata={
                    "sentence_count": len(current_chunk_sentences),
                    "sentence_indices": current_chunk_indices.copy(),
                    "avg_similarity": (
                        float(
                            np.mean(
                                [
                                    cosine_similarity(
                                        embeddings[idx : idx + 1],
                                        embeddings[
                                            current_chunk_indices[
                                                0
                                            ] : current_chunk_indices[0]
                                            + 1
                                        ],
                                    )[0][0]
                                    for idx in current_chunk_indices[1:]
                                ]
                            )
                        )
                        if len(current_chunk_indices) > 1
                        else 1.0
                    ),
                },
            )

            chunks.append(chunk)
            chunk_index += 1

            # Handle overlap for next chunk
            if (
                self.overlap_sentences > 0
                and len(current_chunk_sentences) > self.overlap_sentences
            ):
                # Keep last N sentences for overlap
                overlap_start = len(current_chunk_sentences) - self.overlap_sentences
                current_chunk_sentences = current_chunk_sentences[overlap_start:]
                current_chunk_indices = current_chunk_indices[overlap_start:]
                # Don't increment i - we'll continue with overlap
            else:
                # Start fresh
                current_chunk_sentences = []
                current_chunk_indices = []

        # Handle any remaining sentences
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            token_count = len(self.encoding.encode(chunk_text))

            # Only create chunk if it meets minimum size
            if token_count >= self.min_chunk_size:
                start_char = full_text.find(current_chunk_sentences[0])
                if start_char == -1:
                    start_char = 0

                end_char = start_char + len(chunk_text)

                chunk = self._create_chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    token_count=token_count,
                    metadata={
                        "sentence_count": len(current_chunk_sentences),
                        "sentence_indices": current_chunk_indices,
                        "is_final_chunk": True,
                    },
                )

                chunks.append(chunk)
            else:
                # Merge with previous chunk if too small
                if chunks:
                    last_chunk = chunks[-1]
                    merged_content = last_chunk.content + " " + chunk_text
                    merged_token_count = len(self.encoding.encode(merged_content))

                    # Update last chunk
                    chunks[-1] = self._create_chunk(
                        content=merged_content,
                        chunk_index=last_chunk.chunk_index,
                        start_char=last_chunk.start_char,
                        end_char=last_chunk.start_char + len(merged_content),
                        token_count=merged_token_count,
                        metadata={
                            **last_chunk.metadata,
                            "merged_final_sentences": True,
                            "final_sentence_count": len(current_chunk_sentences),
                        },
                    )

        return chunks
