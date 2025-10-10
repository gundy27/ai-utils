"""Audit logging for metadata store operations."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class MetadataEventType(str, Enum):
    """Types of metadata store audit events."""

    SESSION_CREATED = "session.created"
    SESSION_ACCESSED = "session.accessed"
    MESSAGE_ADDED = "message.added"
    DOCUMENT_CREATED = "document.created"
    DOCUMENT_UPDATED = "document.updated"
    DOCUMENT_DELETED = "document.deleted"


class MetadataAuditEvent(BaseModel):
    """Audit event for metadata operations."""

    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: MetadataEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    document_id: Optional[str] = None

    # Operation details
    operation: str
    outcome: str  # "success", "failure", "error"
    error_message: Optional[str] = None

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data


def emit_metadata_event(
    event_type: MetadataEventType,
    operation: str,
    outcome: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    document_id: Optional[str] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> MetadataAuditEvent:
    """Emit an audit event for metadata operations.

    Args:
        event_type: Type of event
        operation: Operation performed
        outcome: "success", "failure", or "error"
        user_id: User identifier
        session_id: Session identifier
        document_id: Document identifier
        error_message: Error message if outcome is failure/error
        metadata: Additional context

    Returns:
        MetadataAuditEvent: The created audit event
    """
    event = MetadataAuditEvent(
        event_type=event_type,
        operation=operation,
        outcome=outcome,
        user_id=user_id,
        session_id=session_id,
        document_id=document_id,
        error_message=error_message,
        metadata=metadata or {},
    )

    # Log the event
    logger.info("metadata_audit_event", **event.to_log_dict())

    return event
