"""Text chunking utilities for AI applications."""

from .audit import ChunkingAuditEvent, ChunkingEventType, emit_chunking_event
from .base import BaseChunker
from .fixed_size import FixedSizeChunker
from .models import ChunkerConfig, TextChunk
from .token_aware import TokenAwareChunker

__version__ = "0.1.0"

__all__ = [
    "BaseChunker",
    "TextChunk",
    "ChunkerConfig",
    "TokenAwareChunker",
    "FixedSizeChunker",
    "ChunkingAuditEvent",
    "ChunkingEventType",
    "emit_chunking_event",
]
