from __future__ import annotations

import json
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import structlog

from .models import AuditEvent, AuditQuery, AuditQueryResponse

logger = structlog.get_logger(__name__)


class AuditStorage:
    """In-memory audit storage with thread safety."""

    def __init__(self, max_events: int = 100000):
        """
        Initialize audit storage.

        Args:
            max_events: Maximum number of events to keep in memory
        """
        self.max_events = max_events
        self._events: deque = deque(maxlen=max_events)
        self._events_by_tenant: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_events // 10)
        )
        self._events_by_actor: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_events // 20)
        )
        self._lock = threading.RLock()
        self.logger = logger.bind(component="audit_storage")

        self.logger.info("audit_storage_initialized", max_events=max_events)

    def store_event(self, event: AuditEvent) -> None:
        """
        Store an audit event.

        Args:
            event: Audit event to store
        """
        with self._lock:
            # Add to main event store
            self._events.append(event)

            # Add to tenant-specific store
            self._events_by_tenant[event.tenant_id].append(event)

            # Add to actor-specific store
            self._events_by_actor[event.actor_id].append(event)

            self.logger.debug(
                "audit_event_stored",
                event_id=event.event_id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                tenant_id=event.tenant_id,
                total_events=len(self._events),
            )

    def query_events(self, query: AuditQuery) -> AuditQueryResponse:
        """
        Query audit events based on criteria.

        Args:
            query: Query parameters

        Returns:
            Query response with matching events
        """
        with self._lock:
            # Start with tenant-specific events for efficiency
            if query.tenant_id in self._events_by_tenant:
                events = list(self._events_by_tenant[query.tenant_id])
            else:
                events = []

            # Apply filters
            filtered_events = self._apply_filters(events, query)

            # Sort events
            filtered_events = self._sort_events(filtered_events, query)

            # Calculate pagination
            total_count = len(filtered_events)
            start_idx = (query.page - 1) * query.page_size
            end_idx = start_idx + query.page_size

            page_events = filtered_events[start_idx:end_idx]
            total_pages = (total_count + query.page_size - 1) // query.page_size

            self.logger.debug(
                "audit_query_executed",
                tenant_id=query.tenant_id,
                total_matches=total_count,
                page=query.page,
                page_size=query.page_size,
                returned_count=len(page_events),
            )

            return AuditQueryResponse(
                events=page_events,
                total_count=total_count,
                page=query.page,
                page_size=query.page_size,
                total_pages=total_pages,
                has_next=query.page < total_pages,
                has_previous=query.page > 1,
            )

    def _apply_filters(
        self, events: List[AuditEvent], query: AuditQuery
    ) -> List[AuditEvent]:
        """Apply query filters to events."""
        filtered = events

        # Filter by event types
        if query.event_types:
            filtered = [e for e in filtered if e.event_type in query.event_types]

        # Filter by results
        if query.results:
            filtered = [e for e in filtered if e.result in query.results]

        # Filter by actor
        if query.actor_id:
            filtered = [e for e in filtered if e.actor_id == query.actor_id]

        # Filter by resource type
        if query.resource_type:
            filtered = [e for e in filtered if e.resource_type == query.resource_type]

        # Filter by resource ID
        if query.resource_id:
            filtered = [e for e in filtered if e.resource_id == query.resource_id]

        # Filter by time range
        if query.start_time:
            filtered = [e for e in filtered if e.timestamp >= query.start_time]

        if query.end_time:
            filtered = [e for e in filtered if e.timestamp <= query.end_time]

        # Filter by search text
        if query.search_text:
            search_lower = query.search_text.lower()
            filtered = [
                e
                for e in filtered
                if (
                    search_lower in e.description.lower()
                    or search_lower in e.action.lower()
                    or search_lower in e.event_type.lower()
                )
            ]

        return filtered

    def _sort_events(
        self, events: List[AuditEvent], query: AuditQuery
    ) -> List[AuditEvent]:
        """Sort events based on query parameters."""
        reverse = query.sort_order == "desc"

        if query.sort_by == "timestamp":
            return sorted(events, key=lambda e: e.timestamp, reverse=reverse)
        elif query.sort_by == "event_type":
            return sorted(events, key=lambda e: e.event_type, reverse=reverse)
        elif query.sort_by == "actor_id":
            return sorted(events, key=lambda e: e.actor_id, reverse=reverse)
        elif query.sort_by == "result":
            return sorted(events, key=lambda e: e.result, reverse=reverse)
        else:
            # Default to timestamp
            return sorted(events, key=lambda e: e.timestamp, reverse=reverse)

    def get_tenant_stats(self, tenant_id: str, days: int = 30) -> Dict[str, int]:
        """
        Get audit statistics for a tenant.

        Args:
            tenant_id: Tenant ID
            days: Number of days to look back

        Returns:
            Dictionary with statistics
        """
        with self._lock:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

            if tenant_id not in self._events_by_tenant:
                return {
                    "total_events": 0,
                    "successful_events": 0,
                    "failed_events": 0,
                    "unique_actors": 0,
                    "unique_resources": 0,
                }

            events = [
                e
                for e in self._events_by_tenant[tenant_id]
                if e.timestamp >= cutoff_date
            ]

            if not events:
                return {
                    "total_events": 0,
                    "successful_events": 0,
                    "failed_events": 0,
                    "unique_actors": 0,
                    "unique_resources": 0,
                }

            successful = len([e for e in events if e.result == "success"])
            failed = len(
                [e for e in events if e.result in ["failure", "denied", "error"]]
            )
            unique_actors = len(set(e.actor_id for e in events))
            unique_resources = len(
                set(
                    f"{e.resource_type}:{e.resource_id}"
                    for e in events
                    if e.resource_id
                )
            )

            return {
                "total_events": len(events),
                "successful_events": successful,
                "failed_events": failed,
                "unique_actors": unique_actors,
                "unique_resources": unique_resources,
            }

    def export_events(self, tenant_id: str, format: str = "json") -> str:
        """
        Export audit events for a tenant.

        Args:
            tenant_id: Tenant ID
            format: Export format (json, csv)

        Returns:
            Exported data as string
        """
        with self._lock:
            if tenant_id not in self._events_by_tenant:
                return ""

            events = list(self._events_by_tenant[tenant_id])

            if format == "json":
                return json.dumps(
                    [event.model_dump() for event in events], indent=2, default=str
                )
            elif format == "csv":
                # Simple CSV export
                lines = [
                    "event_id,timestamp,event_type,result,actor_id,tenant_id,action,description"
                ]
                for event in events:
                    lines.append(
                        f"{event.event_id},{event.timestamp.isoformat()},{event.event_type},"
                        f"{event.result},{event.actor_id},{event.tenant_id},{event.action},"
                        f'"{event.description}"'
                    )
                return "\n".join(lines)
            else:
                raise ValueError(f"Unsupported export format: {format}")

    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """
        Clean up events older than specified days.

        Args:
            days_to_keep: Number of days to keep events

        Returns:
            Number of events cleaned up
        """
        with self._lock:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

            # Clean main store
            original_count = len(self._events)
            self._events = deque(
                [e for e in self._events if e.timestamp >= cutoff_date],
                maxlen=self.max_events,
            )
            main_cleaned = original_count - len(self._events)

            # Clean tenant stores
            tenant_cleaned = 0
            for tenant_id in list(self._events_by_tenant.keys()):
                original_count = len(self._events_by_tenant[tenant_id])
                self._events_by_tenant[tenant_id] = deque(
                    [
                        e
                        for e in self._events_by_tenant[tenant_id]
                        if e.timestamp >= cutoff_date
                    ],
                    maxlen=self.max_events // 10,
                )
                tenant_cleaned += original_count - len(
                    self._events_by_tenant[tenant_id]
                )

                # Remove empty tenant stores
                if not self._events_by_tenant[tenant_id]:
                    del self._events_by_tenant[tenant_id]

            # Clean actor stores
            actor_cleaned = 0
            for actor_id in list(self._events_by_actor.keys()):
                original_count = len(self._events_by_actor[actor_id])
                self._events_by_actor[actor_id] = deque(
                    [
                        e
                        for e in self._events_by_actor[actor_id]
                        if e.timestamp >= cutoff_date
                    ],
                    maxlen=self.max_events // 20,
                )
                actor_cleaned += original_count - len(self._events_by_actor[actor_id])

                # Remove empty actor stores
                if not self._events_by_actor[actor_id]:
                    del self._events_by_actor[actor_id]

            total_cleaned = main_cleaned + tenant_cleaned + actor_cleaned

            self.logger.info(
                "audit_cleanup_completed",
                days_to_keep=days_to_keep,
                events_cleaned=total_cleaned,
                main_cleaned=main_cleaned,
                tenant_cleaned=tenant_cleaned,
                actor_cleaned=actor_cleaned,
            )

            return total_cleaned

    def get_storage_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        with self._lock:
            return {
                "total_events": len(self._events),
                "tenants": len(self._events_by_tenant),
                "actors": len(self._events_by_actor),
                "max_events": self.max_events,
            }


# Global audit storage instance
audit_storage = AuditStorage()
