"""Audit logging module for auth-secrets-service."""

from .models import (
    AuditEvent,
    AuditEventType,
    AuditQuery,
    AuditQueryResponse,
    AuditResult,
    create_access_event,
    create_audit_event,
    create_auth_event,
    create_secret_event,
)
from .middleware import AuditMiddleware, log_custom_event
from .storage import AuditStorage, audit_storage

__all__ = [
    "AuditEvent",
    "AuditEventType",
    "AuditQuery",
    "AuditQueryResponse",
    "AuditResult",
    "AuditMiddleware",
    "AuditStorage",
    "audit_storage",
    "log_custom_event",
    "create_audit_event",
    "create_auth_event",
    "create_secret_event",
    "create_access_event",
]
