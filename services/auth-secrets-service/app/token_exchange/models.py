"""Token exchange data models and schemas."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Dict, List
from urllib.parse import urlencode

from pydantic import BaseModel, Field, field_validator


class TokenType(str, Enum):
    """Token types for exchange."""

    ACCESS_TOKEN = "access_token"
    REFRESH_TOKEN = "refresh_token"
    ID_TOKEN = "id_token"
    SAML2 = "saml2"
    JWT = "jwt"


class SubjectTokenType(str, Enum):
    """Subject token types."""

    ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"
    REFRESH_TOKEN = "urn:ietf:params:oauth:token-type:refresh_token"
    ID_TOKEN = "urn:ietf:params:oauth:token-type:id_token"
    SAML2 = "urn:ietf:params:oauth:token-type:saml2"
    JWT = "urn:ietf:params:oauth:token-type:jwt"


class RequestedTokenType(str, Enum):
    """Requested token types."""

    ACCESS_TOKEN = "urn:ietf:params:oauth:token-type:access_token"
    REFRESH_TOKEN = "urn:ietf:params:oauth:token-type:refresh_token"


class TokenExchangeRequest(BaseModel):
    """Token exchange request."""

    grant_type: str = "urn:ietf:params:oauth:grant-type:token-exchange"
    subject_token: str
    subject_token_type: SubjectTokenType
    actor_token: Optional[str] = None
    actor_token_type: Optional[SubjectTokenType] = None
    requested_token_type: RequestedTokenType = RequestedTokenType.ACCESS_TOKEN
    audience: Optional[str] = None
    scope: Optional[str] = None
    resource: Optional[str] = None

    @field_validator("grant_type")
    @classmethod
    def validate_grant_type(cls, v):
        """Only support token exchange grant type."""
        if v != "urn:ietf:params:oauth:grant-type:token-exchange":
            raise ValueError("Only token exchange grant type is supported")
        return v


class TokenExchangeResponse(BaseModel):
    """Token exchange response."""

    access_token: str
    issued_token_type: str
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None
    refresh_token: Optional[str] = None

    @classmethod
    def generate_access_token(cls) -> str:
        """Generate a secure access token."""
        return secrets.token_urlsafe(32)


class DelegationRequest(BaseModel):
    """Delegation request for service-to-service communication."""

    source_token: str
    target_audience: str
    target_scopes: List[str] = Field(default_factory=list)
    impersonation: bool = False
    delegation_chain: List[str] = Field(default_factory=list)
    expires_in: int = 3600  # 1 hour default
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DelegationResponse(BaseModel):
    """Delegation response."""

    delegated_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    audience: str
    delegation_chain: List[str]
    issued_at: datetime = Field(default_factory=datetime.utcnow)


class ImpersonationRequest(BaseModel):
    """Impersonation request for admin operations."""

    source_token: str
    target_user_id: str
    target_tenant_id: Optional[str] = None
    impersonation_reason: Optional[str] = None
    target_scopes: List[str] = Field(default_factory=list)
    expires_in: int = 1800  # 30 minutes default for impersonation
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ImpersonationResponse(BaseModel):
    """Impersonation response."""

    impersonation_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str
    impersonated_user_id: str
    impersonated_tenant_id: str
    impersonation_reason: Optional[str] = None
    issued_at: datetime = Field(default_factory=datetime.utcnow)


class TokenExchangeError(BaseModel):
    """Token exchange error response."""

    error: str
    error_description: Optional[str] = None
    error_uri: Optional[str] = None


class TokenExchangeErrorType(str, Enum):
    """Token exchange error types."""

    INVALID_REQUEST = "invalid_request"
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNAUTHORIZED_CLIENT = "unauthorized_client"
    UNSUPPORTED_TOKEN_TYPE = "unsupported_token_type"
    INVALID_SCOPE = "invalid_scope"
    INVALID_AUDIENCE = "invalid_audience"
    INVALID_RESOURCE = "invalid_resource"
    SERVER_ERROR = "server_error"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
    INVALID_DELEGATION = "invalid_delegation"
    IMPERSONATION_DENIED = "impersonation_denied"
    DELEGATION_CHAIN_TOO_LONG = "delegation_chain_too_long"


class DelegationPolicy(BaseModel):
    """Delegation policy for controlling token delegation."""

    policy_id: str
    name: str
    description: Optional[str] = None
    source_scopes: List[str] = Field(default_factory=list)
    target_scopes: List[str] = Field(default_factory=list)
    allowed_audiences: List[str] = Field(default_factory=list)
    max_delegation_depth: int = 3
    requires_impersonation_permission: bool = False
    expires_in_override: Optional[int] = None
    conditions: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TokenExchangeAuditEvent(BaseModel):
    """Audit event for token exchange operations."""

    event_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    actor_id: str
    tenant_id: str
    source_token_type: str
    target_token_type: str
    source_scopes: List[str]
    target_scopes: List[str]
    audience: Optional[str] = None
    delegation_chain: List[str] = Field(default_factory=list)
    impersonation: bool = False
    impersonated_user_id: Optional[str] = None
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


def create_token_exchange_error(
    error: TokenExchangeErrorType,
    description: Optional[str] = None,
    uri: Optional[str] = None,
) -> TokenExchangeError:
    """Create a token exchange error response."""
    return TokenExchangeError(
        error=error.value, error_description=description, error_uri=uri
    )


def validate_delegation_chain(delegation_chain: List[str], max_depth: int = 5) -> bool:
    """Validate delegation chain depth and prevent cycles."""
    if len(delegation_chain) > max_depth:
        return False

    # Check for cycles (same token appears multiple times)
    seen_tokens = set()
    for token in delegation_chain:
        if token in seen_tokens:
            return False
        seen_tokens.add(token)

    return True


def build_delegation_audit_event(
    event_type: str,
    actor_id: str,
    tenant_id: str,
    source_token: str,
    target_token: str,
    source_scopes: List[str],
    target_scopes: List[str],
    success: bool,
    error_message: Optional[str] = None,
    delegation_chain: List[str] = None,
    impersonation: bool = False,
    impersonated_user_id: Optional[str] = None,
    audience: Optional[str] = None,
    metadata: Dict[str, Any] = None,
) -> TokenExchangeAuditEvent:
    """Build an audit event for token exchange operations."""
    return TokenExchangeAuditEvent(
        event_id=secrets.token_urlsafe(16),
        event_type=event_type,
        actor_id=actor_id,
        tenant_id=tenant_id,
        source_token_type="access_token",  # Could be determined from token
        target_token_type="access_token",
        source_scopes=source_scopes,
        target_scopes=target_scopes,
        audience=audience,
        delegation_chain=delegation_chain or [],
        impersonation=impersonation,
        impersonated_user_id=impersonated_user_id,
        success=success,
        error_message=error_message,
        metadata=metadata or {},
    )
