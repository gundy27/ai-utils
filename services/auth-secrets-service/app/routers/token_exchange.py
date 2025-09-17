"""Token exchange API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from ..token_exchange.models import (
    TokenExchangeRequest,
    TokenExchangeResponse,
    TokenExchangeError,
    DelegationRequest,
    DelegationResponse,
    ImpersonationRequest,
    ImpersonationResponse,
    DelegationPolicy,
    TokenExchangeErrorType,
    create_token_exchange_error,
)
from ..token_exchange.service import token_exchange_service
from ..token_exchange.storage import token_exchange_storage
from ..rbac import rbac_middleware, Permission
from ..audit import log_custom_event, AuditEventType, AuditResult

router = APIRouter(prefix="/token-exchange", tags=["token-exchange"])


# Token exchange endpoints
@router.post("/token", response_model=TokenExchangeResponse)
async def exchange_token(
    grant_type: str = Form(...),
    subject_token: str = Form(...),
    subject_token_type: str = Form(...),
    actor_token: Optional[str] = Form(None),
    actor_token_type: Optional[str] = Form(None),
    requested_token_type: str = Form("urn:ietf:params:oauth:token-type:access_token"),
    audience: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
    resource: Optional[str] = Form(None),
):
    """OAuth2 token exchange endpoint."""
    try:
        # Parse token exchange request
        request = TokenExchangeRequest(
            grant_type=grant_type,
            subject_token=subject_token,
            subject_token_type=subject_token_type,
            actor_token=actor_token,
            actor_token_type=actor_token_type,
            requested_token_type=requested_token_type,
            audience=audience,
            scope=scope,
            resource=resource,
        )

        # For now, we'll use a placeholder client_id
        # In a real implementation, this would come from authentication
        client_id = "token-exchange-client"

        # Exchange the token
        response = token_exchange_service.exchange_token(request, client_id)

        # Log successful token exchange
        log_custom_event(
            event_type=AuditEventType.TOKEN_EXCHANGED,
            result=AuditResult.SUCCESS,
            actor_id="system",
            tenant_id="system",
            action="exchange_token",
            description="Token exchange completed successfully",
            resource_type="oauth2_token",
            metadata={
                "subject_token_type": subject_token_type,
                "requested_token_type": requested_token_type,
                "audience": audience,
                "scope": scope,
            },
        )

        return response

    except Exception as e:
        # Log failed token exchange
        log_custom_event(
            event_type=AuditEventType.TOKEN_EXCHANGE_FAILED,
            result=AuditResult.FAILURE,
            actor_id="system",
            tenant_id="system",
            action="exchange_token",
            description=f"Token exchange failed: {str(e)}",
            resource_type="oauth2_token",
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise HTTPException(
            status_code=400,
            detail=create_token_exchange_error(
                TokenExchangeErrorType.INVALID_REQUEST, str(e)
            ).dict(),
        )


# Delegation endpoints
@router.post("/delegate", response_model=DelegationResponse)
async def delegate_token(req: DelegationRequest, request: Request):
    """Delegate a token to another service."""
    # RBAC: Require delegation permission
    user = await rbac_middleware.validate_request(
        request, Permission.DELEGATE_TOKEN, None
    )

    try:
        # For now, we'll use a placeholder client_id
        client_id = "delegation-client"

        # Delegate the token
        response = token_exchange_service.delegate_token(req, client_id)

        # Log successful delegation
        log_custom_event(
            event_type=AuditEventType.TOKEN_DELEGATED,
            result=AuditResult.SUCCESS,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            action="delegate_token",
            description=f"Token delegated to {req.target_audience}",
            resource_type="oauth2_token",
            metadata={
                "target_audience": req.target_audience,
                "target_scopes": req.target_scopes,
                "impersonation": req.impersonation,
                "delegation_chain_length": len(req.delegation_chain),
            },
        )

        return response

    except Exception as e:
        # Log failed delegation
        log_custom_event(
            event_type=AuditEventType.TOKEN_DELEGATION_FAILED,
            result=AuditResult.FAILURE,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            action="delegate_token",
            description=f"Token delegation failed: {str(e)}",
            resource_type="oauth2_token",
            metadata={
                "target_audience": req.target_audience,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise HTTPException(
            status_code=400,
            detail=create_token_exchange_error(
                TokenExchangeErrorType.INVALID_DELEGATION, str(e)
            ).dict(),
        )


@router.post("/impersonate", response_model=ImpersonationResponse)
async def impersonate_user(req: ImpersonationRequest, request: Request):
    """Impersonate another user (admin operation)."""
    # RBAC: Require impersonation permission
    user = await rbac_middleware.validate_request(
        request, Permission.IMPERSONATE_USER, None
    )

    try:
        # For now, we'll use a placeholder client_id
        client_id = "impersonation-client"

        # Impersonate the user
        response = token_exchange_service.impersonate_user(req, client_id)

        # Log successful impersonation (warning level)
        log_custom_event(
            event_type=AuditEventType.USER_IMPERSONATED,
            result=AuditResult.SUCCESS,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            action="impersonate_user",
            description=f"User {req.target_user_id} impersonated by {user.user_id}",
            resource_type="user",
            resource_id=req.target_user_id,
            metadata={
                "impersonated_user_id": req.target_user_id,
                "impersonated_tenant_id": req.target_tenant_id,
                "impersonation_reason": req.impersonation_reason,
                "target_scopes": req.target_scopes,
            },
        )

        return response

    except Exception as e:
        # Log failed impersonation
        log_custom_event(
            event_type=AuditEventType.USER_IMPERSONATION_FAILED,
            result=AuditResult.FAILURE,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            action="impersonate_user",
            description=f"User impersonation failed: {str(e)}",
            resource_type="user",
            resource_id=req.target_user_id,
            metadata={
                "impersonated_user_id": req.target_user_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise HTTPException(
            status_code=403,
            detail=create_token_exchange_error(
                TokenExchangeErrorType.IMPERSONATION_DENIED, str(e)
            ).dict(),
        )


# Delegation policy management
class DelegationPolicyRequest(BaseModel):
    """Delegation policy creation request."""

    policy_id: str
    name: str
    description: Optional[str] = None
    source_scopes: List[str] = []
    target_scopes: List[str] = []
    allowed_audiences: List[str] = []
    max_delegation_depth: int = 3
    requires_impersonation_permission: bool = False
    expires_in_override: Optional[int] = None
    conditions: Dict[str, Any] = {}


@router.post("/policies", response_model=DelegationPolicy)
async def create_delegation_policy(req: DelegationPolicyRequest, request: Request):
    """Create a delegation policy."""
    # RBAC: Require policy management permission
    user = await rbac_middleware.validate_request(
        request, Permission.DELEGATION_POLICY_MANAGE, None
    )

    try:
        # Create the policy
        policy = token_exchange_service.create_delegation_policy(
            policy_id=req.policy_id,
            name=req.name,
            tenant_id=user.tenant_id,
            source_scopes=req.source_scopes,
            target_scopes=req.target_scopes,
            allowed_audiences=req.allowed_audiences,
            max_delegation_depth=req.max_delegation_depth,
            requires_impersonation_permission=req.requires_impersonation_permission,
            expires_in_override=req.expires_in_override,
            conditions=req.conditions,
        )

        # Log successful policy creation
        log_custom_event(
            event_type=AuditEventType.DELEGATION_POLICY_CREATED,
            result=AuditResult.SUCCESS,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            action="create_delegation_policy",
            description=f"Delegation policy '{policy.name}' created",
            resource_type="delegation_policy",
            resource_id=policy.policy_id,
            metadata={
                "policy_name": policy.name,
                "source_scopes": policy.source_scopes,
                "target_scopes": policy.target_scopes,
                "max_delegation_depth": policy.max_delegation_depth,
            },
        )

        return policy

    except Exception as e:
        # Log failed policy creation
        log_custom_event(
            event_type=AuditEventType.DELEGATION_POLICY_CREATION_FAILED,
            result=AuditResult.FAILURE,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            action="create_delegation_policy",
            description=f"Delegation policy creation failed: {str(e)}",
            resource_type="delegation_policy",
            metadata={
                "policy_id": req.policy_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise HTTPException(
            status_code=400, detail=f"Failed to create delegation policy: {str(e)}"
        )


@router.get("/policies", response_model=List[DelegationPolicy])
async def list_delegation_policies(request: Request, tenant_id: Optional[str] = None):
    """List delegation policies."""
    # RBAC: Require policy read permission
    user = await rbac_middleware.validate_request(
        request, Permission.DELEGATION_POLICY_READ, tenant_id or user.tenant_id
    )

    policies = token_exchange_storage.list_delegation_policies(
        tenant_id or user.tenant_id
    )
    return policies


@router.get("/policies/{policy_id}", response_model=DelegationPolicy)
async def get_delegation_policy(policy_id: str, request: Request):
    """Get a delegation policy by ID."""
    # RBAC: Require policy read permission
    user = await rbac_middleware.validate_request(
        request, Permission.DELEGATION_POLICY_READ, None
    )

    policy = token_exchange_storage.get_delegation_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Delegation policy not found")

    return policy


@router.delete("/policies/{policy_id}")
async def delete_delegation_policy(policy_id: str, request: Request):
    """Delete a delegation policy."""
    # RBAC: Require policy management permission
    user = await rbac_middleware.validate_request(
        request, Permission.DELEGATION_POLICY_MANAGE, None
    )

    deleted = token_exchange_storage.delete_delegation_policy(policy_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Delegation policy not found")

    # Log successful policy deletion
    log_custom_event(
        event_type=AuditEventType.DELEGATION_POLICY_DELETED,
        result=AuditResult.SUCCESS,
        actor_id=user.user_id,
        tenant_id=user.tenant_id,
        action="delete_delegation_policy",
        description=f"Delegation policy '{policy_id}' deleted",
        resource_type="delegation_policy",
        resource_id=policy_id,
    )

    return {"message": "Delegation policy deleted successfully"}


# Audit and monitoring endpoints
@router.get("/audit/events")
async def get_token_exchange_audit_events(
    request: Request,
    tenant_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    event_type: Optional[str] = None,
    success: Optional[bool] = None,
    limit: int = 100,
):
    """Get token exchange audit events."""
    # RBAC: Require audit read permission
    user = await rbac_middleware.validate_request(
        request, Permission.AUDIT_READ, tenant_id or user.tenant_id
    )

    events = token_exchange_storage.query_audit_events(
        tenant_id=tenant_id or user.tenant_id,
        actor_id=actor_id,
        event_type=event_type,
        success=success,
        limit=limit,
    )

    return events


@router.get("/audit/stats")
async def get_token_exchange_stats(request: Request, tenant_id: Optional[str] = None):
    """Get token exchange statistics."""
    # RBAC: Require audit read permission
    user = await rbac_middleware.validate_request(
        request, Permission.AUDIT_READ, tenant_id or user.tenant_id
    )

    stats = token_exchange_storage.get_audit_stats(tenant_id or user.tenant_id)
    return stats
