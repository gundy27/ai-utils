"""Audit logging models and utilities for download operations."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from .base import SourceType

logger = structlog.get_logger(__name__)


class DownloadAuditEventType(str, Enum):
    """Types of download audit events."""

    DOWNLOAD_START = "download_start"
    DOWNLOAD_SUCCESS = "download_success"
    DOWNLOAD_FAILURE = "download_failure"
    DOWNLOAD_RETRY = "download_retry"
    DOWNLOAD_TIMEOUT = "download_timeout"
    DOWNLOAD_CANCELLED = "download_cancelled"
    FILE_INTEGRITY_VERIFICATION = "file_integrity_verification"
    FILE_INTEGRITY_FAILURE = "file_integrity_failure"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    BATCH_DOWNLOAD_START = "batch_download_start"
    BATCH_DOWNLOAD_COMPLETE = "batch_download_complete"
    DOWNLOADER_CONFIGURATION_CHANGE = "downloader_configuration_change"


class DownloadAuditSeverity(str, Enum):
    """Severity levels for download audit events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class DownloadAuditEvent(BaseModel):
    """Audit event for download operations."""

    # Event identification
    event_id: str = Field(description="Unique identifier for this audit event")
    event_type: DownloadAuditEventType = Field(description="Type of audit event")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    severity: DownloadAuditSeverity = Field(
        default=DownloadAuditSeverity.INFO, description="Event severity"
    )

    # Actor and tenant information
    actor_id: str = Field(description="ID of the user/system that initiated the action")
    actor_type: str = Field(
        default="user", description="Type of actor (user, system, service)"
    )
    tenant_id: str = Field(description="Tenant/organization identifier")
    session_id: str | None = Field(
        None, description="Session identifier for tracking related events"
    )

    # Download operation details
    source_identifier: str = Field(
        description="Unique identifier for the download source"
    )
    source_type: SourceType = Field(description="Type of download source")
    source_uri: str = Field(description="URI of the download source")
    destination_path: str = Field(description="Local destination path for the download")
    destination_directory: str | None = Field(None, description="Destination directory")

    # File and operation metadata
    file_name: str | None = Field(None, description="Name of the downloaded file")
    file_size: int | None = Field(None, description="Size of the file in bytes")
    file_checksum: str | None = Field(None, description="SHA256 checksum of the file")
    download_duration_ms: float | None = Field(
        None, description="Download duration in milliseconds"
    )
    bytes_downloaded: int | None = Field(None, description="Number of bytes downloaded")

    # Operation result
    success: bool = Field(description="Whether the operation was successful")
    error_message: str | None = Field(
        None, description="Error message if operation failed"
    )
    error_code: str | None = Field(None, description="Error code if operation failed")
    retry_count: int = Field(default=0, description="Number of retry attempts made")

    # Security and compliance
    ip_address: str | None = Field(
        None, description="IP address of the requesting client"
    )
    user_agent: str | None = Field(None, description="User agent string")
    authentication_method: str | None = Field(
        None, description="Authentication method used"
    )
    access_level: str | None = Field(
        None, description="Access level required for this operation"
    )

    # Additional context
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    tags: list[str] = Field(
        default_factory=list, description="Tags for categorization and filtering"
    )
    compliance_flags: list[str] = Field(
        default_factory=list, description="Compliance-related flags"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class DownloadAuditQuery(BaseModel):
    """Query parameters for searching audit events."""

    # Time range
    start_time: datetime | None = Field(None, description="Start time for query range")
    end_time: datetime | None = Field(None, description="End time for query range")

    # Filtering
    tenant_id: str | None = Field(None, description="Filter by tenant ID")
    actor_id: str | None = Field(None, description="Filter by actor ID")
    source_identifier: str | None = Field(
        None, description="Filter by source identifier"
    )
    source_type: SourceType | None = Field(None, description="Filter by source type")
    event_type: DownloadAuditEventType | None = Field(
        None, description="Filter by event type"
    )
    success: bool | None = Field(None, description="Filter by success status")
    severity: DownloadAuditSeverity | None = Field(
        None, description="Filter by severity"
    )

    # Pagination
    limit: int = Field(default=100, description="Maximum number of results to return")
    offset: int = Field(default=0, description="Number of results to skip")

    # Sorting
    sort_by: str = Field(default="timestamp", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc or desc)")

    # Tags and metadata
    tags: list[str] | None = Field(None, description="Filter by tags")
    compliance_flags: list[str] | None = Field(
        None, description="Filter by compliance flags"
    )


class DownloadAuditResult(BaseModel):
    """Result of an audit query."""

    events: list[DownloadAuditEvent] = Field(description="List of audit events")
    total_count: int = Field(description="Total number of events matching the query")
    has_more: bool = Field(description="Whether there are more results available")
    query: DownloadAuditQuery = Field(
        description="The query that produced these results"
    )


class DownloadAuditStats(BaseModel):
    """Statistics about download audit events."""

    tenant_id: str = Field(description="Tenant ID these stats apply to")
    time_range_start: datetime = Field(description="Start of the time range")
    time_range_end: datetime = Field(description="End of the time range")

    # Event counts
    total_events: int = Field(description="Total number of events")
    successful_downloads: int = Field(description="Number of successful downloads")
    failed_downloads: int = Field(description="Number of failed downloads")
    retry_events: int = Field(description="Number of retry events")

    # Event types
    event_type_counts: dict[str, int] = Field(description="Count of events by type")
    source_type_counts: dict[str, int] = Field(
        description="Count of events by source type"
    )

    # Performance metrics
    average_download_time_ms: float | None = Field(
        None, description="Average download time"
    )
    total_bytes_downloaded: int | None = Field(
        None, description="Total bytes downloaded"
    )

    # Security metrics
    suspicious_activity_count: int = Field(
        default=0, description="Number of suspicious activities"
    )
    rate_limit_violations: int = Field(
        default=0, description="Number of rate limit violations"
    )
    integrity_failures: int = Field(
        default=0, description="Number of file integrity failures"
    )

    # Top actors and sources
    top_actors: list[dict[str, Any]] = Field(
        default_factory=list, description="Top actors by activity"
    )
    top_sources: list[dict[str, Any]] = Field(
        default_factory=list, description="Top sources by downloads"
    )


def create_download_audit_event(
    event_type: DownloadAuditEventType,
    actor_id: str,
    tenant_id: str,
    source_identifier: str,
    source_type: SourceType,
    source_uri: str,
    destination_path: str,
    success: bool,
    event_id: str | None = None,
    severity: DownloadAuditSeverity = DownloadAuditSeverity.INFO,
    **kwargs: Any,
) -> DownloadAuditEvent:
    """Create a download audit event with common fields populated.

    Args:
        event_type: Type of audit event
        actor_id: ID of the actor performing the action
        tenant_id: Tenant identifier
        source_identifier: Unique identifier for the source
        source_type: Type of download source
        source_uri: URI of the source
        destination_path: Local destination path
        success: Whether the operation was successful
        event_id: Optional custom event ID (generated if not provided)
        severity: Severity level of the event
        **kwargs: Additional fields for the audit event

    Returns:
        DownloadAuditEvent instance
    """
    import uuid

    if event_id is None:
        event_id = str(uuid.uuid4())

    return DownloadAuditEvent(
        event_id=event_id,
        event_type=event_type,
        severity=severity,
        actor_id=actor_id,
        tenant_id=tenant_id,
        source_identifier=source_identifier,
        source_type=source_type,
        source_uri=source_uri,
        destination_path=destination_path,
        success=success,
        **kwargs,
    )


def create_suspicious_activity_event(
    actor_id: str,
    tenant_id: str,
    source_identifier: str,
    source_type: SourceType,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> DownloadAuditEvent:
    """Create a suspicious activity audit event.

    Args:
        actor_id: ID of the actor
        tenant_id: Tenant identifier
        source_identifier: Source being accessed
        source_type: Type of source
        reason: Reason for flagging as suspicious
        metadata: Additional metadata about the suspicious activity

    Returns:
        DownloadAuditEvent for suspicious activity
    """
    return create_download_audit_event(
        event_type=DownloadAuditEventType.SUSPICIOUS_ACTIVITY,
        actor_id=actor_id,
        tenant_id=tenant_id,
        source_identifier=source_identifier,
        source_type=source_type,
        source_uri="",  # Not applicable for suspicious activity
        destination_path="",  # Not applicable for suspicious activity
        success=False,  # Suspicious activity is never considered successful
        severity=DownloadAuditSeverity.WARNING,
        error_message=f"Suspicious activity detected: {reason}",
        metadata=metadata or {},
        tags=["security", "suspicious_activity"],
        compliance_flags=["security_incident"],
    )
