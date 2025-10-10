"""Job queue for background processing in RAG applications."""

from .audit import JobAuditEvent, JobEventType, emit_job_event
from .base import BaseJobQueue
from .models import Job, JobRequest, JobStats, JobStatus

__version__ = "0.1.0"

__all__ = [
    "BaseJobQueue",
    "Job",
    "JobRequest",
    "JobStats",
    "JobStatus",
    "JobAuditEvent",
    "JobEventType",
    "emit_job_event",
]

# Import backends
from .backends import InMemoryQueue  # noqa: F401

__all__.append("InMemoryQueue")
