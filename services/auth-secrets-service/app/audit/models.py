from __future__ import annotations

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Authentication events
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_LOGIN_FAILED = "auth.login_failed"
    AUTH_TOKEN_ISSUED = "auth.token_issued"
    AUTH_TOKEN_VALIDATED = "auth.token_validated"
    AUTH_TOKEN_EXPIRED = "auth.token_expired"
    AUTH_TOKEN_INVALID = "auth.token_invalid"

    # Secret management events
    SECRET_FETCH = "secret.fetch"
    SECRET_FETCH_FAILED = "secret.fetch_failed"
    SECRET_ROTATE = "secret.rotate"
    SECRET_ROTATE_FAILED = "secret.rotate_failed"
    SECRET_DELETE = "secret.delete"
    SECRET_DELETE_FAILED = "secret.delete_failed"

    # Authorization events
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    PERMISSION_CHECK = "permission.check"
    TENANT_ACCESS = "tenant.access"

    # Administrative events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    ROLE_ASSIGNED = "role.assigned"
    ROLE_REVOKED = "role.revoked"
    TENANT_CREATED = "tenant.created"
    TENANT_UPDATED = "tenant.updated"

    # OAuth2 events
    CLIENT_REGISTERED = "oauth2.client_registered"
    CLIENT_REGISTRATION_FAILED = "oauth2.client_registration_failed"
    CLIENT_UPDATED = "oauth2.client_updated"
    CLIENT_DELETED = "oauth2.client_deleted"
    AUTHORIZATION_GRANTED = "oauth2.authorization_granted"
    AUTHORIZATION_FAILED = "oauth2.authorization_failed"
    AUTHORIZATION_DENIED = "oauth2.authorization_denied"
    TOKEN_ISSUED = "oauth2.token_issued"
    TOKEN_ISSUANCE_FAILED = "oauth2.token_issuance_failed"
    TOKEN_REFRESHED = "oauth2.token_refreshed"
    TOKEN_REFRESH_FAILED = "oauth2.token_refresh_failed"
    TOKEN_REVOKED = "oauth2.token_revoked"

    # Token exchange events
    TOKEN_EXCHANGED = "token_exchange.exchanged"
    TOKEN_EXCHANGE_FAILED = "token_exchange.exchange_failed"
    TOKEN_DELEGATED = "token_exchange.delegated"
    TOKEN_DELEGATION_FAILED = "token_exchange.delegation_failed"
    USER_IMPERSONATED = "token_exchange.impersonated"
    USER_IMPERSONATION_FAILED = "token_exchange.impersonation_failed"
    DELEGATION_POLICY_CREATED = "token_exchange.delegation_policy_created"
    DELEGATION_POLICY_CREATION_FAILED = (
        "token_exchange.delegation_policy_creation_failed"
    )
    DELEGATION_POLICY_UPDATED = "token_exchange.delegation_policy_updated"
    DELEGATION_POLICY_DELETED = "token_exchange.delegation_policy_deleted"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    CONFIG_CHANGED = "config.changed"
    ERROR_OCCURRED = "error.occurred"


class AuditResult(str, Enum):
    """Result of an audit event."""

    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    ERROR = "error"


class AuditEvent(BaseModel):
    """Audit event model."""

    # Unique identifier
    event_id: str = Field(default_factory=lambda: str(uuid4()))

    # Timestamp
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    timestamp_unix: float = Field(default_factory=time.time)

    # Event details
    event_type: AuditEventType
    result: AuditResult

    # Actor information
    actor_id: str
    actor_type: str = "user"  # user, service, system
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None

    # Resource information
    tenant_id: str
    resource_type: Optional[str] = None  # secret, user, tenant, etc.
    resource_id: Optional[str] = None
    resource_scope: Optional[str] = None

    # Action details
    action: str
    description: str

    # Request/Response information
    request_id: Optional[str] = None
    method: Optional[str] = None  # HTTP method
    path: Optional[str] = None  # HTTP path
    status_code: Optional[int] = None

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)

    # Compliance fields
    data_classification: str = "internal"  # public, internal, confidential, restricted
    retention_days: int = 2555  # 7 years default for compliance

    model_config = {
        "use_enum_values": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        },
    }


class AuditQuery(BaseModel):
    """Query parameters for audit log retrieval."""

    # Filtering
    tenant_id: str
    event_types: Optional[list[AuditEventType]] = None
    results: Optional[list[AuditResult]] = None
    actor_id: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

    # Time range
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    # Search
    search_text: Optional[str] = None  # Search in description, action, etc.

    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)

    # Sorting
    sort_by: str = Field(default="timestamp")
    sort_order: str = Field(default="desc")  # asc or desc


class AuditQueryResponse(BaseModel):
    """Response for audit log queries."""

    events: list[AuditEvent]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


def create_audit_event(
    event_type: AuditEventType,
    result: AuditResult,
    actor_id: str,
    tenant_id: str,
    action: str,
    description: str,
    **kwargs: Any,
) -> AuditEvent:
    """Create an audit event with common fields."""

    return AuditEvent(
        event_type=event_type,
        result=result,
        actor_id=actor_id,
        tenant_id=tenant_id,
        action=action,
        description=description,
        **kwargs,
    )


def create_auth_event(
    event_type: AuditEventType,
    result: AuditResult,
    actor_id: str,
    tenant_id: str,
    token_info: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> AuditEvent:
    """Create an authentication-related audit event."""

    description = f"Authentication event: {event_type.value}"
    if token_info:
        description += f" for token {token_info.get('token_id', 'unknown')}"

    return create_audit_event(
        event_type=event_type,
        result=result,
        actor_id=actor_id,
        tenant_id=tenant_id,
        action="authenticate",
        description=description,
        resource_type="auth",
        metadata=token_info or {},
        **kwargs,
    )


def create_secret_event(
    event_type: AuditEventType,
    result: AuditResult,
    actor_id: str,
    tenant_id: str,
    secret_ref: str,
    scope: str,
    secret_name: str,
    **kwargs: Any,
) -> AuditEvent:
    """Create a secret-related audit event."""

    description = f"Secret {event_type.value}: {scope}/{secret_name}"

    return create_audit_event(
        event_type=event_type,
        result=result,
        actor_id=actor_id,
        tenant_id=tenant_id,
        action="secret_access",
        description=description,
        resource_type="secret",
        resource_id=secret_ref,
        resource_scope=scope,
        metadata={
            "secret_name": secret_name,
            "secret_scope": scope,
        },
        **kwargs,
    )


def create_access_event(
    event_type: AuditEventType,
    result: AuditResult,
    actor_id: str,
    tenant_id: str,
    permission: str,
    resource: str,
    **kwargs: Any,
) -> AuditEvent:
    """Create an access control audit event."""

    description = f"Access {result.value}: {permission} on {resource}"

    return create_audit_event(
        event_type=event_type,
        result=result,
        actor_id=actor_id,
        tenant_id=tenant_id,
        action="access_control",
        description=description,
        resource_type="access",
        metadata={
            "permission": permission,
            "resource": resource,
        },
        **kwargs,
    )
