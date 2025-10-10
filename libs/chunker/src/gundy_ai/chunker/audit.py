"""Audit logging for text chunking operations."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ChunkingEventType(str, Enum):
    """Types of chunking audit events."""

    CHUNKING_STARTED = "chunking.started"
    CHUNKING_COMPLETED = "chunking.completed"
    CHUNKING_FAILED = "chunking.failed"


class ChunkingAuditEvent(BaseModel):
    """Audit event for chunking operations."""

    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: ChunkingEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Chunking information
    strategy: str  # "token_aware", "fixed_size"
    max_tokens: Optional[int] = None
    chunk_size: Optional[int] = None

    # Input
    input_length: int  # Characters in input text
    input_tokens: Optional[int] = None

    # Output
    chunks_created: Optional[int] = None
    total_output_tokens: Optional[int] = None

    # Performance
    processing_time_ms: Optional[float] = None

    # Outcome
    outcome: str  # "success", "failure", "error"
    error_message: Optional[str] = None

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data


def emit_chunking_event(
    event_type: ChunkingEventType,
    strategy: str,
    input_length: int,
    outcome: str,
    max_tokens: Optional[int] = None,
    chunk_size: Optional[int] = None,
    input_tokens: Optional[int] = None,
    chunks_created: Optional[int] = None,
    total_output_tokens: Optional[int] = None,
    processing_time_ms: Optional[float] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ChunkingAuditEvent:
    """Emit an audit event for chunking operations.

    Args:
        event_type: Type of event (started, completed, failed)
        strategy: Chunking strategy used
        input_length: Length of input text in characters
        outcome: "success", "failure", or "error"
        max_tokens: Maximum tokens per chunk (if applicable)
        chunk_size: Chunk size in characters (if applicable)
        input_tokens: Total tokens in input (if known)
        chunks_created: Number of chunks created
        total_output_tokens: Total tokens across all chunks
        processing_time_ms: Processing time in milliseconds
        error_message: Error message if outcome is failure/error
        metadata: Additional context

    Returns:
        ChunkingAuditEvent: The created audit event
    """
    event = ChunkingAuditEvent(
        event_type=event_type,
        strategy=strategy,
        max_tokens=max_tokens,
        chunk_size=chunk_size,
        input_length=input_length,
        input_tokens=input_tokens,
        chunks_created=chunks_created,
        total_output_tokens=total_output_tokens,
        processing_time_ms=processing_time_ms,
        outcome=outcome,
        error_message=error_message,
        metadata=metadata or {},
    )

    # Log the event
    logger.info("chunking_audit_event", **event.to_log_dict())

    return event
