"""Data models for embedding operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingResult(BaseModel):
    """Result from embedding generation.

    Contains the generated embeddings along with metadata about
    the operation including cost, latency, and token usage.
    """

    embeddings: List[List[float]] = Field(
        description="List of embedding vectors, one per input text"
    )
    model: str = Field(description="Model used for embedding generation")
    dimensions: int = Field(description="Dimensionality of embeddings")
    total_tokens: int = Field(description="Total tokens processed")
    texts_count: int = Field(description="Number of texts embedded")

    # Cost and performance metadata
    latency_ms: float = Field(description="Time taken in milliseconds")
    estimated_cost_usd: Optional[float] = Field(
        default=None, description="Estimated cost in USD (if available)"
    )

    # Additional metadata
    provider: str = Field(description="Provider name (openai, cohere, etc.)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Provider-specific metadata"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                "model": "text-embedding-3-small",
                "dimensions": 1536,
                "total_tokens": 10,
                "texts_count": 2,
                "latency_ms": 150.5,
                "estimated_cost_usd": 0.00001,
                "provider": "openai",
                "metadata": {},
            }
        }
    )


class ProviderConfig(BaseModel):
    """Configuration for an embedding provider."""

    provider_name: str = Field(description="Provider identifier")
    model: str = Field(description="Model to use for embeddings")
    api_key: Optional[str] = Field(default=None, description="API key (if required)")
    api_base: Optional[str] = Field(default=None, description="Custom API base URL")
    max_batch_size: int = Field(
        default=100, description="Maximum texts to embed in one request"
    )
    timeout_seconds: int = Field(default=60, description="Request timeout")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "provider_name": "openai",
                "model": "text-embedding-3-small",
                "max_batch_size": 100,
                "timeout_seconds": 60,
                "max_retries": 3,
            }
        }
    )
