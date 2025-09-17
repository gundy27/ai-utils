"""Token exchange storage layer for policies and audit events."""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import structlog

from .models import (
    DelegationPolicy,
    TokenExchangeAuditEvent,
    DelegationRequest,
    ImpersonationRequest,
)

logger = structlog.get_logger(__name__)


class InMemoryTokenExchangeStorage:
    """In-memory storage for token exchange policies and audit events."""

    def __init__(self, max_events: int = 50000):
        """Initialize the storage."""
        self.logger = logger.bind(component="token_exchange_storage")
        self.max_events = max_events
        self._lock = threading.Lock()

        # Storage containers
        self._delegation_policies: Dict[str, DelegationPolicy] = {}
        self._audit_events: deque = deque(maxlen=max_events)

        self.logger.info(
            "token_exchange_storage_initialized",
            max_events=max_events,
        )

    # Delegation policy management
    def store_delegation_policy(self, policy: DelegationPolicy) -> None:
        """Store a delegation policy."""
        with self._lock:
            self._delegation_policies[policy.policy_id] = policy

            self.logger.debug(
                "delegation_policy_stored",
                policy_id=policy.policy_id,
                name=policy.name,
                tenant_id=policy.tenant_id,
                max_delegation_depth=policy.max_delegation_depth,
            )

    def get_delegation_policy(self, policy_id: str) -> Optional[DelegationPolicy]:
        """Get a delegation policy by ID."""
        with self._lock:
            policy = self._delegation_policies.get(policy_id)
            if policy and not policy.is_active:
                return None
            return policy

    def list_delegation_policies(
        self, tenant_id: Optional[str] = None
    ) -> List[DelegationPolicy]:
        """List delegation policies, optionally filtered by tenant."""
        with self._lock:
            policies = list(self._delegation_policies.values())

            if tenant_id:
                policies = [p for p in policies if p.tenant_id == tenant_id]

            # Only return active policies
            return [p for p in policies if p.is_active]

    def find_matching_policy(
        self,
        source_scopes: List[str],
        target_scopes: List[str],
        audience: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Optional[DelegationPolicy]:
        """Find a delegation policy that matches the request."""
        with self._lock:
            policies = self.list_delegation_policies(tenant_id)

            for policy in policies:
                # Check source scopes match
                if policy.source_scopes:
                    if not all(
                        scope in source_scopes for scope in policy.source_scopes
                    ):
                        continue

                # Check target scopes are allowed
                if policy.target_scopes:
                    if not all(
                        scope in policy.target_scopes for scope in target_scopes
                    ):
                        continue

                # Check audience is allowed
                if audience and policy.allowed_audiences:
                    if audience not in policy.allowed_audiences:
                        continue

                return policy

            return None

    def update_delegation_policy(
        self, policy_id: str, **updates
    ) -> Optional[DelegationPolicy]:
        """Update a delegation policy."""
        with self._lock:
            if policy_id not in self._delegation_policies:
                return None

            policy = self._delegation_policies[policy_id]

            # Update fields
            for key, value in updates.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)

            policy.updated_at = datetime.utcnow()

            self.logger.debug(
                "delegation_policy_updated",
                policy_id=policy_id,
                updates=list(updates.keys()),
            )

            return policy

    def delete_delegation_policy(self, policy_id: str) -> bool:
        """Delete a delegation policy."""
        with self._lock:
            if policy_id in self._delegation_policies:
                del self._delegation_policies[policy_id]
                self.logger.debug("delegation_policy_deleted", policy_id=policy_id)
                return True
            return False

    # Audit event management
    def store_audit_event(self, event: TokenExchangeAuditEvent) -> None:
        """Store an audit event."""
        with self._lock:
            self._audit_events.append(event)

            self.logger.debug(
                "token_exchange_audit_event_stored",
                event_id=event.event_id,
                event_type=event.event_type,
                actor_id=event.actor_id,
                tenant_id=event.tenant_id,
                success=event.success,
            )

    def query_audit_events(
        self,
        tenant_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        success: Optional[bool] = None,
        limit: int = 100,
    ) -> List[TokenExchangeAuditEvent]:
        """Query audit events with filtering."""
        with self._lock:
            events = list(self._audit_events)

            # Apply filters
            if tenant_id:
                events = [e for e in events if e.tenant_id == tenant_id]

            if actor_id:
                events = [e for e in events if e.actor_id == actor_id]

            if event_type:
                events = [e for e in events if e.event_type == event_type]

            if start_time:
                events = [e for e in events if e.timestamp >= start_time]

            if end_time:
                events = [e for e in events if e.timestamp <= end_time]

            if success is not None:
                events = [e for e in events if e.success == success]

            # Sort by timestamp (newest first)
            events.sort(key=lambda e: e.timestamp, reverse=True)

            # Limit results
            return events[:limit]

    def get_audit_stats(self, tenant_id: Optional[str] = None) -> Dict[str, int]:
        """Get audit statistics."""
        with self._lock:
            events = list(self._audit_events)

            if tenant_id:
                events = [e for e in events if e.tenant_id == tenant_id]

            stats = {
                "total_events": len(events),
                "successful_exchanges": len([e for e in events if e.success]),
                "failed_exchanges": len([e for e in events if not e.success]),
                "delegation_events": len(
                    [e for e in events if "delegation" in e.event_type]
                ),
                "impersonation_events": len([e for e in events if e.impersonation]),
            }

            return stats

    def cleanup_old_events(self, days: int = 30) -> int:
        """Clean up old audit events."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)

        with self._lock:
            original_count = len(self._audit_events)

            # Remove old events
            self._audit_events = deque(
                [e for e in self._audit_events if e.timestamp > cutoff_time],
                maxlen=self.max_events,
            )

            cleaned_count = original_count - len(self._audit_events)

            if cleaned_count > 0:
                self.logger.info(
                    "old_audit_events_cleaned",
                    cleaned_count=cleaned_count,
                    days=days,
                )

            return cleaned_count

    # Cleanup and maintenance
    def cleanup_expired_items(self) -> None:
        """Clean up expired items."""
        with self._lock:
            self.cleanup_old_events()

    def get_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        with self._lock:
            return {
                "delegation_policies": len(self._delegation_policies),
                "audit_events": len(self._audit_events),
            }


# Global storage instance
token_exchange_storage = InMemoryTokenExchangeStorage()
