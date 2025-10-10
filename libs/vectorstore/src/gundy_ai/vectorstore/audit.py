"""Audit logging for vector store operations."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class VectorStoreEventType(str, Enum):
    """Types of vector store audit events."""

    VECTORSTORE_UPSERT = "vectorstore.upsert"
    VECTORSTORE_QUERY = "vectorstore.query"
    VECTORSTORE_DELETE = "vectorstore.delete"
    VECTORSTORE_HEALTH_CHECK = "vectorstore.health_check"


class VectorStoreAuditEvent(BaseModel):
    """Audit event for vector store operations."""

    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: VectorStoreEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Store information
    adapter: str  # "chromadb", "faiss", etc.
    collection: str

    # Operation details
    operation: str  # "upsert", "query", "delete", "health_check"
    vector_count: Optional[int] = None
    top_k: Optional[int] = None
    filter_applied: bool = False

    # Performance
    latency_ms: Optional[float] = None

    # Outcome
    outcome: str  # "success", "failure", "error"
    error_message: Optional[str] = None

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        # Redact embeddings from logs per security requirement
        if "embeddings" in data.get("metadata", {}):
            data["metadata"]["embeddings"] = "<redacted>"
        return data


def emit_vectorstore_event(
    event_type: VectorStoreEventType,
    adapter: str,
    collection: str,
    operation: str,
    outcome: str,
    vector_count: Optional[int] = None,
    top_k: Optional[int] = None,
    filter_applied: bool = False,
    latency_ms: Optional[float] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> VectorStoreAuditEvent:
    """Emit an audit event for vector store operations.

    Note: Embeddings are redacted from logs per security requirements.

    Args:
        event_type: Type of event
        adapter: Adapter name (chromadb, faiss, etc.)
        collection: Collection/index name
        operation: Operation performed
        outcome: "success", "failure", or "error"
        vector_count: Number of vectors involved
        top_k: Top K for queries
        filter_applied: Whether metadata filter was used
        latency_ms: Processing time
        error_message: Error message if outcome is failure/error
        metadata: Additional context (embeddings will be redacted)

    Returns:
        VectorStoreAuditEvent: The created audit event
    """
    event = VectorStoreAuditEvent(
        event_type=event_type,
        adapter=adapter,
        collection=collection,
        operation=operation,
        vector_count=vector_count,
        top_k=top_k,
        filter_applied=filter_applied,
        latency_ms=latency_ms,
        outcome=outcome,
        error_message=error_message,
        metadata=metadata or {},
    )

    # Log the event (embeddings already redacted by to_log_dict)
    logger.info("vectorstore_audit_event", **event.to_log_dict())

    return event
