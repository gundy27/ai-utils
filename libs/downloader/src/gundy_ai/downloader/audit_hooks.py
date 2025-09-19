"""Audit hooks for download operations."""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

import structlog

from .audit import (
    DownloadAuditEvent,
    DownloadAuditQuery,
    DownloadAuditResult,
    DownloadAuditStats,
)

logger = structlog.get_logger(__name__)


class AuditHook(ABC):
    """Abstract base class for audit hooks."""

    @abstractmethod
    async def log_download_event(self, event: DownloadAuditEvent) -> None:
        """Log a download audit event.

        Args:
            event: The audit event to log
        """
        pass

    @abstractmethod
    async def query_audit_events(
        self, query: DownloadAuditQuery
    ) -> DownloadAuditResult:
        """Query audit events based on the given criteria.

        Args:
            query: Query parameters for filtering and pagination

        Returns:
            DownloadAuditResult with matching events
        """
        pass

    @abstractmethod
    async def get_audit_stats(
        self,
        tenant_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> DownloadAuditStats:
        """Get audit statistics for a tenant.

        Args:
            tenant_id: Tenant identifier
            start_time: Optional start time for the statistics
            end_time: Optional end time for the statistics

        Returns:
            DownloadAuditStats with aggregated data
        """
        pass


class NoOpAuditHook(AuditHook):
    """No-operation audit hook that discards all events."""

    async def log_download_event(self, event: DownloadAuditEvent) -> None:
        """Discard the audit event."""
        pass

    async def query_audit_events(
        self, query: DownloadAuditQuery
    ) -> DownloadAuditResult:
        """Return empty result."""
        return DownloadAuditResult(
            events=[],
            total_count=0,
            has_more=False,
            query=query,
        )

    async def get_audit_stats(
        self,
        tenant_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> DownloadAuditStats:
        """Return empty stats."""
        now = datetime.utcnow()
        return DownloadAuditStats(
            tenant_id=tenant_id,
            time_range_start=start_time or now,
            time_range_end=end_time or now,
            total_events=0,
            successful_downloads=0,
            failed_downloads=0,
            retry_events=0,
            event_type_counts={},
            source_type_counts={},
        )


class LoggingAuditHook(AuditHook):
    """Audit hook that logs events to structured logs."""

    def __init__(self, log_level: str = "info"):
        """Initialize logging audit hook.

        Args:
            log_level: Log level to use for audit events (debug, info, warning, error, critical)
        """
        self.log_level = log_level
        self.logger = logger.bind(audit_hook="logging")

    async def log_download_event(self, event: DownloadAuditEvent) -> None:
        """Log audit event to structured logs."""
        log_data = {
            "audit_event_id": event.event_id,
            "audit_event_type": event.event_type,
            "audit_severity": event.severity,
            "actor_id": event.actor_id,
            "actor_type": event.actor_type,
            "tenant_id": event.tenant_id,
            "session_id": event.session_id,
            "source_identifier": event.source_identifier,
            "source_type": event.source_type,
            "source_uri": event.source_uri,
            "destination_path": event.destination_path,
            "file_name": event.file_name,
            "file_size": event.file_size,
            "file_checksum": event.file_checksum,
            "download_duration_ms": event.download_duration_ms,
            "bytes_downloaded": event.bytes_downloaded,
            "success": event.success,
            "error_message": event.error_message,
            "error_code": event.error_code,
            "retry_count": event.retry_count,
            "ip_address": event.ip_address,
            "user_agent": event.user_agent,
            "authentication_method": event.authentication_method,
            "access_level": event.access_level,
            "metadata": event.metadata,
            "tags": event.tags,
            "compliance_flags": event.compliance_flags,
            "timestamp": event.timestamp.isoformat(),
        }

        if self.log_level == "debug":
            self.logger.debug("download_audit_event", **log_data)
        elif self.log_level == "info":
            self.logger.info("download_audit_event", **log_data)
        elif self.log_level == "warning":
            self.logger.warning("download_audit_event", **log_data)
        elif self.log_level == "error":
            self.logger.error("download_audit_event", **log_data)
        elif self.log_level == "critical":
            self.logger.critical("download_audit_event", **log_data)

    async def query_audit_events(
        self, query: DownloadAuditQuery
    ) -> DownloadAuditResult:
        """Query is not supported by logging hook."""
        self.logger.warning(
            "audit_query_not_supported",
            query_type="logging_hook",
            message="Logging audit hook does not support querying events",
        )
        return DownloadAuditResult(
            events=[],
            total_count=0,
            has_more=False,
            query=query,
        )

    async def get_audit_stats(
        self,
        tenant_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> DownloadAuditStats:
        """Stats are not supported by logging hook."""
        self.logger.warning(
            "audit_stats_not_supported",
            query_type="logging_hook",
            message="Logging audit hook does not support statistics",
        )
        now = datetime.utcnow()
        return DownloadAuditStats(
            tenant_id=tenant_id,
            time_range_start=start_time or now,
            time_range_end=end_time or now,
            total_events=0,
            successful_downloads=0,
            failed_downloads=0,
            retry_events=0,
            event_type_counts={},
            source_type_counts={},
        )


class FileAuditHook(AuditHook):
    """Audit hook that stores events in JSON files."""

    def __init__(self, audit_file_path: str | Path, max_file_size_mb: int = 100):
        """Initialize file audit hook.

        Args:
            audit_file_path: Path to the audit log file
            max_file_size_mb: Maximum file size before rotation
        """
        self.audit_file_path = Path(audit_file_path)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.logger = logger.bind(audit_hook="file")
        self._events_buffer: list[DownloadAuditEvent] = []
        self._buffer_lock = asyncio.Lock()

        # Ensure directory exists
        self.audit_file_path.parent.mkdir(parents=True, exist_ok=True)

    async def log_download_event(self, event: DownloadAuditEvent) -> None:
        """Store audit event in file."""
        async with self._buffer_lock:
            self._events_buffer.append(event)

            # Flush buffer if it gets too large
            if len(self._events_buffer) >= 100:  # Flush every 100 events
                await self._flush_buffer()

    async def _flush_buffer(self) -> None:
        """Flush the events buffer to file."""
        if not self._events_buffer:
            return

        try:
            # Check if we need to rotate the file
            if (
                self.audit_file_path.exists()
                and self.audit_file_path.stat().st_size > self.max_file_size_bytes
            ):
                await self._rotate_file()

            # Write events to file
            with open(self.audit_file_path, "a", encoding="utf-8") as f:
                for event in self._events_buffer:
                    f.write(json.dumps(event.dict(), default=str) + "\n")

            self.logger.debug(
                "audit_events_flushed",
                count=len(self._events_buffer),
                file_path=str(self.audit_file_path),
            )

            self._events_buffer.clear()

        except Exception as e:
            self.logger.error(
                "audit_flush_error",
                error=str(e),
                buffer_size=len(self._events_buffer),
                file_path=str(self.audit_file_path),
            )

    async def _rotate_file(self) -> None:
        """Rotate the audit file."""
        if not self.audit_file_path.exists():
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        rotated_path = self.audit_file_path.with_suffix(f".{timestamp}.jsonl")
        self.audit_file_path.rename(rotated_path)

        self.logger.info(
            "audit_file_rotated",
            old_path=str(self.audit_file_path),
            new_path=str(rotated_path),
        )

    async def query_audit_events(
        self, query: DownloadAuditQuery
    ) -> DownloadAuditResult:
        """Query events from the audit file."""
        events: list[DownloadAuditEvent] = []

        if not self.audit_file_path.exists():
            return DownloadAuditResult(
                events=[],
                total_count=0,
                has_more=False,
                query=query,
            )

        try:
            with open(self.audit_file_path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        event_data = json.loads(line)
                        event = DownloadAuditEvent(**event_data)
                        events.append(event)
                    except Exception as e:
                        self.logger.warning(
                            "audit_event_parse_error",
                            error=str(e),
                            line=line[:100],  # Log first 100 chars
                        )

            # Apply filters
            filtered_events = self._filter_events(events, query)

            # Apply pagination
            start_idx = query.offset
            end_idx = start_idx + query.limit
            paginated_events = filtered_events[start_idx:end_idx]

            return DownloadAuditResult(
                events=paginated_events,
                total_count=len(filtered_events),
                has_more=end_idx < len(filtered_events),
                query=query,
            )

        except Exception as e:
            self.logger.error("audit_query_error", error=str(e), query=query.dict())
            return DownloadAuditResult(
                events=[],
                total_count=0,
                has_more=False,
                query=query,
            )

    def _filter_events(
        self, events: list[DownloadAuditEvent], query: DownloadAuditQuery
    ) -> list[DownloadAuditEvent]:
        """Filter events based on query criteria."""
        filtered = events

        if query.start_time:
            filtered = [e for e in filtered if e.timestamp >= query.start_time]
        if query.end_time:
            filtered = [e for e in filtered if e.timestamp <= query.end_time]
        if query.tenant_id:
            filtered = [e for e in filtered if e.tenant_id == query.tenant_id]
        if query.actor_id:
            filtered = [e for e in filtered if e.actor_id == query.actor_id]
        if query.source_identifier:
            filtered = [
                e for e in filtered if e.source_identifier == query.source_identifier
            ]
        if query.source_type:
            filtered = [e for e in filtered if e.source_type == query.source_type]
        if query.event_type:
            filtered = [e for e in filtered if e.event_type == query.event_type]
        if query.success is not None:
            filtered = [e for e in filtered if e.success == query.success]
        if query.severity:
            filtered = [e for e in filtered if e.severity == query.severity]

        # Sort events
        reverse = query.sort_order == "desc"
        if query.sort_by == "timestamp":
            filtered.sort(key=lambda e: e.timestamp, reverse=reverse)

        return filtered

    async def get_audit_stats(
        self,
        tenant_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> DownloadAuditStats:
        """Get audit statistics from the audit file."""
        # Create a query to get all events for the tenant
        query = DownloadAuditQuery(
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            limit=10000,  # Large limit to get all events
        )

        result = await self.query_audit_events(query)
        events = result.events

        # Calculate statistics
        now = datetime.utcnow()
        stats = DownloadAuditStats(
            tenant_id=tenant_id,
            time_range_start=start_time or now,
            time_range_end=end_time or now,
            total_events=len(events),
            successful_downloads=sum(
                1 for e in events if e.success and e.event_type == "download_success"
            ),
            failed_downloads=sum(
                1
                for e in events
                if not e.success and e.event_type == "download_failure"
            ),
            retry_events=sum(1 for e in events if e.event_type == "download_retry"),
            event_type_counts={},
            source_type_counts={},
            suspicious_activity_count=sum(
                1 for e in events if e.event_type == "suspicious_activity"
            ),
            rate_limit_violations=sum(
                1 for e in events if e.event_type == "rate_limit_exceeded"
            ),
            integrity_failures=sum(
                1 for e in events if e.event_type == "file_integrity_failure"
            ),
        )

        # Count event types and source types
        for event in events:
            stats.event_type_counts[event.event_type] = (
                stats.event_type_counts.get(event.event_type, 0) + 1
            )
            stats.source_type_counts[event.source_type] = (
                stats.source_type_counts.get(event.source_type, 0) + 1
            )

        # Calculate performance metrics
        download_times = [
            e.download_duration_ms for e in events if e.download_duration_ms is not None
        ]
        if download_times:
            stats.average_download_time_ms = sum(download_times) / len(download_times)

        bytes_downloaded = [
            e.bytes_downloaded for e in events if e.bytes_downloaded is not None
        ]
        if bytes_downloaded:
            stats.total_bytes_downloaded = sum(bytes_downloaded)

        # Calculate top actors and sources
        actor_counts: dict[str, int] = {}
        source_counts: dict[str, int] = {}

        for event in events:
            actor_counts[event.actor_id] = actor_counts.get(event.actor_id, 0) + 1
            source_counts[event.source_identifier] = (
                source_counts.get(event.source_identifier, 0) + 1
            )

        stats.top_actors = [
            {"actor_id": actor, "count": count}
            for actor, count in sorted(
                actor_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]
        stats.top_sources = [
            {"source_identifier": source, "count": count}
            for source, count in sorted(
                source_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        return stats


class DatabaseAuditHook(AuditHook):
    """Audit hook that stores events in a database."""

    def __init__(self, database_url: str, table_name: str = "download_audit_events"):
        """Initialize database audit hook.

        Args:
            database_url: Database connection URL
            table_name: Name of the audit events table
        """
        self.database_url = database_url
        self.table_name = table_name
        self.logger = logger.bind(audit_hook="database")

    async def log_download_event(self, event: DownloadAuditEvent) -> None:
        """Store audit event in database."""
        # This would be implemented with actual database operations
        # For now, we'll log that it would be stored
        self.logger.info(
            "audit_event_would_be_stored",
            event_id=event.event_id,
            event_type=event.event_type,
            actor_id=event.actor_id,
            tenant_id=event.tenant_id,
            database_url=self.database_url,
            table_name=self.table_name,
        )

    async def query_audit_events(
        self, query: DownloadAuditQuery
    ) -> DownloadAuditResult:
        """Query events from database."""
        # This would be implemented with actual database queries
        self.logger.info(
            "audit_query_would_be_executed",
            query=query.dict(),
            database_url=self.database_url,
            table_name=self.table_name,
        )

        return DownloadAuditResult(
            events=[],
            total_count=0,
            has_more=False,
            query=query,
        )

    async def get_audit_stats(
        self,
        tenant_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> DownloadAuditStats:
        """Get audit statistics from database."""
        # This would be implemented with actual database aggregation queries
        self.logger.info(
            "audit_stats_would_be_calculated",
            tenant_id=tenant_id,
            start_time=start_time,
            end_time=end_time,
            database_url=self.database_url,
            table_name=self.table_name,
        )

        now = datetime.utcnow()
        return DownloadAuditStats(
            tenant_id=tenant_id,
            time_range_start=start_time or now,
            time_range_end=end_time or now,
            total_events=0,
            successful_downloads=0,
            failed_downloads=0,
            retry_events=0,
            event_type_counts={},
            source_type_counts={},
        )


class CompositeAuditHook(AuditHook):
    """Composite audit hook that forwards events to multiple hooks."""

    def __init__(self, hooks: list[AuditHook]):
        """Initialize composite audit hook.

        Args:
            hooks: List of audit hooks to forward events to
        """
        self.hooks = hooks
        self.logger = logger.bind(audit_hook="composite")

    async def log_download_event(self, event: DownloadAuditEvent) -> None:
        """Forward audit event to all hooks."""
        tasks = []
        for hook in self.hooks:
            tasks.append(hook.log_download_event(event))

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(
                "composite_audit_error", error=str(e), event_id=event.event_id
            )

    async def query_audit_events(
        self, query: DownloadAuditQuery
    ) -> DownloadAuditResult:
        """Query events from the first available hook."""
        for hook in self.hooks:
            try:
                result = await hook.query_audit_events(query)
                if result.events:  # Return first non-empty result
                    return result
            except Exception as e:
                self.logger.warning(
                    "audit_query_hook_error",
                    error=str(e),
                    hook_type=hook.__class__.__name__,
                )

        return DownloadAuditResult(
            events=[],
            total_count=0,
            has_more=False,
            query=query,
        )

    async def get_audit_stats(
        self,
        tenant_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> DownloadAuditStats:
        """Get stats from the first available hook."""
        for hook in self.hooks:
            try:
                return await hook.get_audit_stats(tenant_id, start_time, end_time)
            except Exception as e:
                self.logger.warning(
                    "audit_stats_hook_error",
                    error=str(e),
                    hook_type=hook.__class__.__name__,
                )

        # Fallback to empty stats
        now = datetime.utcnow()
        return DownloadAuditStats(
            tenant_id=tenant_id,
            time_range_start=start_time or now,
            time_range_end=end_time or now,
            total_events=0,
            successful_downloads=0,
            failed_downloads=0,
            retry_events=0,
            event_type_counts={},
            source_type_counts={},
        )
