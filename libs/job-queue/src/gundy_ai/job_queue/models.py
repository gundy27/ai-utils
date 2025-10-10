"""Data models for job queue."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Job status states."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobRequest(BaseModel):
    """Request to create a job."""

    job_type: str = Field(description="Type of job (document_ingest, etc.)")
    payload: Dict[str, Any] = Field(description="Job payload data")
    idempotency_key: Optional[str] = Field(
        default=None, description="Idempotency key to prevent duplicates"
    )
    priority: int = Field(default=0, description="Job priority (higher = first)")
    max_retries: int = Field(default=3, description="Maximum retry attempts")


class Job(BaseModel):
    """Job model."""

    id: str = Field(description="Unique job identifier")
    job_type: str = Field(description="Type of job")
    status: JobStatus = Field(description="Current job status")
    payload: Dict[str, Any] = Field(description="Job payload data")
    idempotency_key: Optional[str] = Field(default=None, description="Idempotency key")

    # Lifecycle timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Retry tracking
    attempts: int = Field(default=0, description="Number of processing attempts")
    max_retries: int = Field(default=3, description="Maximum retry attempts")

    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    # Priority
    priority: int = Field(default=0, description="Job priority")


class JobStats(BaseModel):
    """Queue statistics."""

    total_jobs: int = Field(description="Total jobs")
    queued: int = Field(description="Jobs in queue")
    processing: int = Field(description="Jobs being processed")
    completed: int = Field(description="Completed jobs")
    failed: int = Field(description="Failed jobs")
