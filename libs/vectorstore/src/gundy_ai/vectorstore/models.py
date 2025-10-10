"""Data models for vector store operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class VectorDocument(BaseModel):
    """A document with embedding vector and metadata."""

    id: str = Field(description="Unique document identifier")
    embedding: List[float] = Field(description="Embedding vector")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    text: Optional[str] = Field(default=None, description="Original text (optional)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc_123",
                "embedding": [0.1, 0.2, 0.3],
                "metadata": {"title": "Sample", "page": 1},
                "text": "Sample document text",
            }
        }
    )


class QueryResult(BaseModel):
    """Result from similarity search."""

    id: str = Field(description="Document identifier")
    score: float = Field(description="Similarity score (higher = more similar)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document metadata"
    )
    text: Optional[str] = Field(default=None, description="Original text if stored")
    embedding: Optional[List[float]] = Field(
        default=None, description="Embedding vector if requested"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "doc_123",
                "score": 0.95,
                "metadata": {"title": "Sample"},
                "text": "Sample text",
            }
        }
    )


class StoreConfig(BaseModel):
    """Configuration for vector store."""

    adapter_name: str = Field(description="Adapter identifier (chromadb, faiss, etc.)")
    persist_directory: Optional[str] = Field(
        default=None, description="Directory for persistence"
    )
    collection_name: str = Field(
        default="documents", description="Collection/index name"
    )
    embedding_dimension: Optional[int] = Field(
        default=None, description="Embedding vector dimensions"
    )
    distance_metric: str = Field(
        default="cosine", description="Distance metric (cosine, euclidean, dot)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "adapter_name": "chromadb",
                "persist_directory": "./vector_db",
                "collection_name": "documents",
                "embedding_dimension": 1536,
                "distance_metric": "cosine",
            }
        }
    )
