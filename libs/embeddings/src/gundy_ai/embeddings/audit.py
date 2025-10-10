"""Audit logging for embedding operations."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class EmbeddingEventType(str, Enum):
    """Types of embedding audit events."""

    EMBEDDING_REQUESTED = "embedding.requested"
    EMBEDDING_COMPLETED = "embedding.completed"
    EMBEDDING_FAILED = "embedding.failed"
    PROVIDER_HEALTH_CHECK = "provider.health_check"


class EmbeddingAuditEvent(BaseModel):
    """Audit event for embedding operations."""

    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EmbeddingEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Provider information
    provider: str
    model: str

    # Request details
    texts_count: Optional[int] = None
    total_tokens: Optional[int] = None
    batch_size: Optional[int] = None

    # Performance and cost
    latency_ms: Optional[float] = None
    estimated_cost_usd: Optional[float] = None

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


def emit_embedding_event(
    event_type: EmbeddingEventType,
    provider: str,
    model: str,
    outcome: str,
    texts_count: Optional[int] = None,
    total_tokens: Optional[int] = None,
    batch_size: Optional[int] = None,
    latency_ms: Optional[float] = None,
    estimated_cost_usd: Optional[float] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> EmbeddingAuditEvent:
    """Emit an audit event for embedding operations.

    Args:
        event_type: Type of event (requested, completed, failed)
        provider: Provider name (e.g., "openai")
        model: Model being used
        outcome: "success", "failure", or "error"
        texts_count: Number of texts being embedded
        total_tokens: Total tokens processed
        batch_size: Batch size used
        latency_ms: Processing time in milliseconds
        estimated_cost_usd: Estimated cost in USD
        error_message: Error message if outcome is failure/error
        metadata: Additional context

    Returns:
        EmbeddingAuditEvent: The created audit event
    """
    event = EmbeddingAuditEvent(
        event_type=event_type,
        provider=provider,
        model=model,
        texts_count=texts_count,
        total_tokens=total_tokens,
        batch_size=batch_size,
        latency_ms=latency_ms,
        estimated_cost_usd=estimated_cost_usd,
        outcome=outcome,
        error_message=error_message,
        metadata=metadata or {},
    )

    # Log the event
    logger.info("embedding_audit_event", **event.to_log_dict())

    return event
