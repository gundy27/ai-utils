"""Audit logging for job queue operations."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class JobEventType(str, Enum):
    """Types of job queue audit events."""

    JOB_QUEUED = "job.queued"
    JOB_STARTED = "job.started"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_RETRY = "job.retry"
    JOB_CANCELLED = "job.cancelled"


class JobAuditEvent(BaseModel):
    """Audit event for job operations."""

    # Event identification
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: JobEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Job information
    job_id: str
    job_type: str
    idempotency_key: Optional[str] = None

    # Status
    status: str
    attempts: int = 0

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


def emit_job_event(
    event_type: JobEventType,
    job_id: str,
    job_type: str,
    status: str,
    outcome: str,
    idempotency_key: Optional[str] = None,
    attempts: int = 0,
    processing_time_ms: Optional[float] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> JobAuditEvent:
    """Emit an audit event for job operations.

    Args:
        event_type: Type of event
        job_id: Job identifier
        job_type: Type of job
        status: Current job status
        outcome: "success", "failure", or "error"
        idempotency_key: Idempotency key
        attempts: Number of attempts
        processing_time_ms: Processing time
        error_message: Error message if outcome is failure/error
        metadata: Additional context

    Returns:
        JobAuditEvent: The created audit event
    """
    event = JobAuditEvent(
        event_type=event_type,
        job_id=job_id,
        job_type=job_type,
        idempotency_key=idempotency_key,
        status=status,
        attempts=attempts,
        processing_time_ms=processing_time_ms,
        outcome=outcome,
        error_message=error_message,
        metadata=metadata or {},
    )

    # Log the event
    logger.info("job_audit_event", **event.to_log_dict())

    return event
