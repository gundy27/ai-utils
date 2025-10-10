"""Audit logging for document extraction operations."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class ExtractionEventType(str, Enum):
    """Types of extraction audit events."""

    EXTRACTOR_INVOKED = "extractor.invoked"
    EXTRACTOR_SUCCEEDED = "extractor.succeeded"
    EXTRACTOR_FAILED = "extractor.failed"
    PARSER_REGISTERED = "parser.registered"
    PARSER_HEALTH_CHECK = "parser.health_check"


class ExtractionAuditEvent(BaseModel):
    """Audit event for extraction operations."""

    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: ExtractionEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Parser information
    parser_name: str
    parser_version: Optional[str] = None

    # File information
    file_path: str
    file_size: Optional[int] = None
    file_extension: Optional[str] = None

    # Outcome
    outcome: str  # "success", "failure", "error"
    error_message: Optional[str] = None

    # Performance metrics
    processing_time_ms: Optional[float] = None
    chunks_extracted: Optional[int] = None
    total_characters: Optional[int] = None

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = self.model_dump()
        data["timestamp"] = self.timestamp.isoformat()
        return data


def emit_extraction_event(
    event_type: ExtractionEventType,
    parser_name: str,
    file_path: str,
    outcome: str,
    parser_version: Optional[str] = None,
    error_message: Optional[str] = None,
    processing_time_ms: Optional[float] = None,
    chunks_extracted: Optional[int] = None,
    total_characters: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ExtractionAuditEvent:
    """Emit an audit event for extraction operations.

    Args:
        event_type: Type of event (invoked, succeeded, failed)
        parser_name: Name of the parser being used
        file_path: Path to file being parsed
        outcome: "success", "failure", or "error"
        parser_version: Version of parser (optional)
        error_message: Error message if outcome is failure/error
        processing_time_ms: Time taken to process in milliseconds
        chunks_extracted: Number of chunks extracted
        total_characters: Total characters extracted
        metadata: Additional context

    Returns:
        ExtractionAuditEvent: The created audit event
    """
    import os

    event = ExtractionAuditEvent(
        event_type=event_type,
        parser_name=parser_name,
        parser_version=parser_version,
        file_path=file_path,
        file_size=os.path.getsize(file_path) if os.path.exists(file_path) else None,
        file_extension=os.path.splitext(file_path)[1],
        outcome=outcome,
        error_message=error_message,
        processing_time_ms=processing_time_ms,
        chunks_extracted=chunks_extracted,
        total_characters=total_characters,
        metadata=metadata or {},
    )

    # Log the event
    logger.info("extraction_audit_event", **event.to_log_dict())

    return event
