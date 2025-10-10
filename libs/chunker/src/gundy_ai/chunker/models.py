"""Data models for text chunking."""

from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class TextChunk(BaseModel):
    """A chunk of text with metadata.

    Represents a portion of text that has been chunked,
    with token/character counts and positional information.
    """

    chunk_id: str = Field(description="Unique identifier for this chunk")
    text: str = Field(description="Chunk text content")
    token_count: int = Field(description="Number of tokens in chunk")
    char_count: int = Field(description="Number of characters in chunk")
    chunk_index: int = Field(description="Index of chunk in sequence (0-based)")
    span_start: int = Field(description="Character offset start in original text")
    span_end: int = Field(description="Character offset end in original text")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (strategy, overlap, etc.)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chunk_id": "chunk_0",
                "text": "This is a sample chunk.",
                "token_count": 6,
                "char_count": 23,
                "chunk_index": 0,
                "span_start": 0,
                "span_end": 23,
                "metadata": {"strategy": "token_aware", "overlap_tokens": 10},
            }
        }
    )


class ChunkerConfig(BaseModel):
    """Configuration for text chunking."""

    strategy: str = Field(description="Chunking strategy (token_aware, fixed_size)")
    max_tokens: int = Field(default=512, description="Maximum tokens per chunk")
    overlap_tokens: int = Field(default=50, description="Overlap in tokens")
    chunk_size: int = Field(
        default=1000, description="Chunk size in characters (fixed_size)"
    )
    overlap_size: int = Field(
        default=100, description="Overlap in characters (fixed_size)"
    )
    encoding_name: str = Field(
        default="cl100k_base", description="Tiktoken encoding (for token_aware)"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "strategy": "token_aware",
                "max_tokens": 512,
                "overlap_tokens": 50,
                "encoding_name": "cl100k_base",
            }
        }
    )
