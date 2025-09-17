"""Embedding generation and management utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog
from openai import AsyncOpenAI

from .base import BaseProcessor, ProcessingResult, ProcessorConfig
from .document import TextChunk, ProcessedDocument

logger = structlog.get_logger(__name__)


class EmbeddingModel(Enum):
    """Supported embedding models."""

    OPENAI_TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"
    OPENAI_TEXT_EMBEDDING_3_LARGE = "text-embedding-3-large"
    OPENAI_TEXT_EMBEDDING_ADA_002 = "text-embedding-ada-002"


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""

    model: EmbeddingModel = EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL
    api_key: str | None = None
    base_url: str | None = None
    max_batch_size: int = 100
    embedding_dimensions: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EmbeddingVector:
    """An embedding vector with metadata."""

    vector: list[float]
    text: str
    model: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate embedding vector."""
        if not self.vector:
            raise ValueError("Vector cannot be empty")
        if not isinstance(self.vector, list):
            raise ValueError("Vector must be a list")
        if not all(isinstance(x, (int, float)) for x in self.vector):
            raise ValueError("Vector must contain only numbers")


@dataclass
class EmbeddedDocument:
    """A document with embedded chunks."""

    document: ProcessedDocument
    embeddings: list[EmbeddingVector]

    def get_embedding_count(self) -> int:
        """Get total number of embeddings."""
        return len(self.embeddings)

    def get_total_embeddings_tokens(self) -> int:
        """Get total token count for embeddings."""
        return sum(emb.token_count for emb in self.embeddings)


class EmbeddingProcessor(BaseProcessor[ProcessedDocument, EmbeddedDocument]):
    """Processor for generating embeddings from text chunks."""

    def __init__(self, config: ProcessorConfig, embedding_config: EmbeddingConfig):
        """Initialize embedding processor."""
        super().__init__(config)
        self.embedding_config = embedding_config
        self.client = AsyncOpenAI(
            api_key=embedding_config.api_key, base_url=embedding_config.base_url
        )

    def validate_input(self, input_data: ProcessedDocument) -> bool:
        """Validate input is a processed document."""
        return isinstance(input_data, ProcessedDocument) and len(input_data.chunks) > 0

    async def process(
        self, document: ProcessedDocument
    ) -> ProcessingResult[EmbeddedDocument]:
        """Generate embeddings for document chunks."""
        try:
            embeddings = await self._generate_embeddings(document.chunks)

            embedded_doc = EmbeddedDocument(document=document, embeddings=embeddings)

            return ProcessingResult(
                success=True,
                data=embedded_doc,
                metadata={
                    "embedding_count": len(embeddings),
                    "model": self.embedding_config.model.value,
                    "total_tokens": sum(emb.token_count for emb in embeddings),
                },
            )

        except Exception as e:
            self.logger.error("embedding.generation.error", error=str(e))
            return ProcessingResult(
                success=False, error=f"Failed to generate embeddings: {str(e)}"
            )

    async def _generate_embeddings(
        self, chunks: list[TextChunk]
    ) -> list[EmbeddingVector]:
        """Generate embeddings for text chunks."""
        embeddings = []

        # Process chunks in batches
        for i in range(0, len(chunks), self.embedding_config.max_batch_size):
            batch = chunks[i : i + self.embedding_config.max_batch_size]
            batch_embeddings = await self._process_batch(batch)
            embeddings.extend(batch_embeddings)

            self.logger.info(
                "embedding.batch.completed",
                batch_start=i,
                batch_size=len(batch),
                total_processed=len(embeddings),
            )

        return embeddings

    async def _process_batch(self, chunks: list[TextChunk]) -> list[EmbeddingVector]:
        """Process a batch of chunks to generate embeddings."""
        texts = [chunk.content for chunk in chunks]

        try:
            # Prepare request parameters
            request_params = {
                "model": self.embedding_config.model.value,
                "input": texts,
            }

            # Add dimensions if specified
            if self.embedding_config.embedding_dimensions:
                request_params["dimensions"] = (
                    self.embedding_config.embedding_dimensions
                )

            # Generate embeddings
            response = await self.client.embeddings.create(**request_params)

            embeddings = []
            for i, embedding_data in enumerate(response.data):
                chunk = chunks[i]

                # Estimate token count (rough approximation)
                token_count = len(chunk.content.split()) * 1.3  # Rough estimate

                embedding = EmbeddingVector(
                    vector=embedding_data.embedding,
                    text=chunk.content,
                    model=self.embedding_config.model.value,
                    token_count=int(token_count),
                    metadata={
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "original_metadata": chunk.metadata,
                    },
                )

                embeddings.append(embedding)

            return embeddings

        except Exception as e:
            self.logger.error(
                "embedding.batch.error", error=str(e), batch_size=len(chunks)
            )
            raise


class EmbeddingStorage:
    """Base class for embedding storage backends."""

    async def store_embeddings(self, embedded_doc: EmbeddedDocument) -> bool:
        """Store embeddings for a document."""
        raise NotImplementedError

    async def search_embeddings(
        self, query_embedding: list[float], limit: int = 10
    ) -> list[EmbeddingVector]:
        """Search for similar embeddings."""
        raise NotImplementedError

    async def get_embeddings_by_document(
        self, document_id: str
    ) -> list[EmbeddingVector]:
        """Get all embeddings for a document."""
        raise NotImplementedError


class InMemoryEmbeddingStorage(EmbeddingStorage):
    """In-memory storage for embeddings (for testing/demo purposes)."""

    def __init__(self):
        """Initialize in-memory storage."""
        self.embeddings: list[EmbeddingVector] = []
        self.document_embeddings: dict[str, list[EmbeddingVector]] = {}

    async def store_embeddings(self, embedded_doc: EmbeddedDocument) -> bool:
        """Store embeddings in memory."""
        try:
            doc_id = embedded_doc.document.metadata.filename

            # Store embeddings
            self.embeddings.extend(embedded_doc.embeddings)
            self.document_embeddings[doc_id] = embedded_doc.embeddings

            logger.info(
                "embedding.storage.stored",
                document_id=doc_id,
                count=len(embedded_doc.embeddings),
            )
            return True

        except Exception as e:
            logger.error("embedding.storage.error", error=str(e))
            return False

    async def search_embeddings(
        self, query_embedding: list[float], limit: int = 10
    ) -> list[EmbeddingVector]:
        """Search for similar embeddings using cosine similarity."""
        if not self.embeddings:
            return []

        # Calculate cosine similarities
        similarities = []
        for embedding in self.embeddings:
            similarity = self._cosine_similarity(query_embedding, embedding.vector)
            similarities.append((similarity, embedding))

        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x[0], reverse=True)
        return [emb for _, emb in similarities[:limit]]

    async def get_embeddings_by_document(
        self, document_id: str
    ) -> list[EmbeddingVector]:
        """Get embeddings for a specific document."""
        return self.document_embeddings.get(document_id, [])

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)
