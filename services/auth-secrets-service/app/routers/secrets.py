from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..errors import error_response
from ..providers.base import SecretRef
from ..providers.dispatcher import get_provider
from ..rbac.middleware import rbac_middleware
from ..rbac.models import Permission
from ..audit.middleware import log_custom_event
from ..audit.models import AuditEventType, AuditResult

router = APIRouter()


class FetchSecretRequest(BaseModel):
    tenant_id: str
    scope: str
    name: str
    version: str | None = None


class FetchSecretResponse(BaseModel):
    value: str
    metadata: dict[str, str] | None = None


@router.post("/fetch", response_model=FetchSecretResponse)
async def fetch_secret(req: FetchSecretRequest, request: Request):
    # RBAC: Require SECRET_READ permission for the target tenant
    user = await rbac_middleware.validate_request(
        request, Permission.SECRET_READ, req.tenant_id
    )

    provider = get_provider()
    secret_ref = SecretRef(req.tenant_id, req.scope, req.name, req.version)

    try:
        value, meta = provider.get_secret(secret_ref)

        # Log successful secret fetch
        log_custom_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.SUCCESS,
            actor_id=user.user_id,
            tenant_id=req.tenant_id,
            action="fetch_secret",
            description=f"Secret fetched: {req.scope}/{req.name}",
            resource_type="secret",
            resource_id=f"{req.scope}/{req.name}",
            resource_scope=req.scope,
            metadata={
                "secret_name": req.name,
                "secret_scope": req.scope,
                "secret_version": req.version,
                "has_metadata": meta is not None,
            },
        )

        return FetchSecretResponse(value=value, metadata=meta)

    except KeyError:
        # Log failed secret fetch
        log_custom_event(
            event_type=AuditEventType.SECRET_FETCH_FAILED,
            result=AuditResult.FAILURE,
            actor_id=user.user_id,
            tenant_id=req.tenant_id,
            action="fetch_secret",
            description=f"Secret not found: {req.scope}/{req.name}",
            resource_type="secret",
            resource_id=f"{req.scope}/{req.name}",
            resource_scope=req.scope,
            metadata={
                "secret_name": req.name,
                "secret_scope": req.scope,
                "secret_version": req.version,
                "error": "secret_not_found",
            },
        )

        return error_response(404, "secret_not_found", "Secret not found")


class RotateSecretRequest(BaseModel):
    tenant_id: str
    scope: str
    name: str
    reason: str | None = None
    dry_run: bool | None = None


class RotateSecretResponse(BaseModel):
    previous_version: str | None = None
    new_version: str | None = "v2"
    status: str = "scheduled"


@router.post("/rotate", response_model=RotateSecretResponse)
async def rotate_secret(req: RotateSecretRequest, request: Request):
    # RBAC: Require SECRET_ROTATE permission for the target tenant
    user = await rbac_middleware.validate_request(
        request, Permission.SECRET_ROTATE, req.tenant_id
    )

    provider = get_provider()
    secret_ref = SecretRef(req.tenant_id, req.scope, req.name)

    try:
        meta = provider.rotate_secret(
            secret_ref,
            req.reason or None,
            bool(req.dry_run),
        )

        # Log successful secret rotation
        log_custom_event(
            event_type=AuditEventType.SECRET_ROTATE,
            result=AuditResult.SUCCESS,
            actor_id=user.user_id,
            tenant_id=req.tenant_id,
            action="rotate_secret",
            description=f"Secret rotated: {req.scope}/{req.name}",
            resource_type="secret",
            resource_id=f"{req.scope}/{req.name}",
            resource_scope=req.scope,
            metadata={
                "secret_name": req.name,
                "secret_scope": req.scope,
                "reason": req.reason,
                "dry_run": bool(req.dry_run),
                "previous_version": meta.get("previous_version"),
                "new_version": meta.get("new_version"),
                "status": meta.get("status"),
            },
        )

        return RotateSecretResponse(
            previous_version=meta.get("previous_version"),
            new_version=meta.get("new_version"),
            status=meta.get("status", "ok"),
        )

    except Exception as e:
        # Log failed secret rotation
        log_custom_event(
            event_type=AuditEventType.SECRET_ROTATE_FAILED,
            result=AuditResult.FAILURE,
            actor_id=user.user_id,
            tenant_id=req.tenant_id,
            action="rotate_secret",
            description=f"Secret rotation failed: {req.scope}/{req.name}",
            resource_type="secret",
            resource_id=f"{req.scope}/{req.name}",
            resource_scope=req.scope,
            metadata={
                "secret_name": req.name,
                "secret_scope": req.scope,
                "reason": req.reason,
                "dry_run": bool(req.dry_run),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise


class ListSecretsRequest(BaseModel):
    tenant_id: str
    scope: str = ""


class ListSecretsResponse(BaseModel):
    secrets: list[str]


@router.post("/list", response_model=ListSecretsResponse)
async def list_secrets(req: ListSecretsRequest, request: Request):
    # RBAC: Require SECRET_READ permission for the target tenant
    user = await rbac_middleware.validate_request(
        request, Permission.SECRET_READ, req.tenant_id
    )

    provider = get_provider()

    # Check if provider supports listing (Vault does, others might not)
    if hasattr(provider, "list_secrets"):
        try:
            secrets = provider.list_secrets(req.tenant_id, req.scope)

            # Log successful secret listing
            log_custom_event(
                event_type=AuditEventType.SECRET_FETCH,
                result=AuditResult.SUCCESS,
                actor_id=user.user_id,
                tenant_id=req.tenant_id,
                action="list_secrets",
                description=f"Listed secrets for {req.scope or 'all scopes'}",
                resource_type="secret",
                metadata={
                    "scope": req.scope,
                    "secret_count": len(secrets),
                },
            )

            return ListSecretsResponse(secrets=secrets)

        except Exception as e:
            # Log failed secret listing
            log_custom_event(
                event_type=AuditEventType.SECRET_FETCH_FAILED,
                result=AuditResult.FAILURE,
                actor_id=user.user_id,
                tenant_id=req.tenant_id,
                action="list_secrets",
                description=f"Failed to list secrets for {req.scope or 'all scopes'}",
                resource_type="secret",
                metadata={
                    "scope": req.scope,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            raise
    else:
        # Provider doesn't support listing
        log_custom_event(
            event_type=AuditEventType.SECRET_FETCH_FAILED,
            result=AuditResult.FAILURE,
            actor_id=user.user_id,
            tenant_id=req.tenant_id,
            action="list_secrets",
            description="Secret listing not supported by current provider",
            resource_type="secret",
            metadata={
                "provider": type(provider).__name__,
                "error": "list_secrets_not_supported",
            },
        )

        return error_response(
            501, "not_supported", "Secret listing not supported by current provider"
        )
