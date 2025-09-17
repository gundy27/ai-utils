from __future__ import annotations

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ..auth.jwt_service import issue_jwt, validate_jwt
from ..rbac.middleware import rbac_middleware
from ..rbac.models import Permission, Role
from ..audit.middleware import log_custom_event
from ..audit.models import AuditEventType, AuditResult

router = APIRouter()


class IssueJwtRequest(BaseModel):
    subject: str
    tenant_id: str
    scopes: list[str]
    audience: str
    ttl_s: int
    roles: list[str] | None = None


class IssueJwtResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/jwt/issue", response_model=IssueJwtResponse)
async def issue_jwt_route(req: IssueJwtRequest, request: Request):
    # RBAC: Require JWT_ISSUE permission for the target tenant
    user = await rbac_middleware.validate_request(
        request, Permission.JWT_ISSUE, req.tenant_id
    )

    # Parse roles from request
    roles = None
    if req.roles:
        try:
            roles = [
                Role(role) for role in req.roles if role in Role.__members__.values()
            ]
        except ValueError:
            # Invalid role provided - could log warning here
            pass

    res = issue_jwt(
        req.subject, req.tenant_id, req.scopes, req.audience, req.ttl_s, roles
    )

    # Log successful JWT issuance
    log_custom_event(
        event_type=AuditEventType.AUTH_TOKEN_ISSUED,
        result=AuditResult.SUCCESS,
        actor_id=user.user_id,
        tenant_id=req.tenant_id,
        action="issue_jwt",
        description=f"JWT issued for subject {req.subject}",
        resource_type="auth",
        metadata={
            "subject": req.subject,
            "audience": req.audience,
            "scopes": req.scopes,
            "ttl_s": req.ttl_s,
            "roles": [role.value for role in roles] if roles else [],
            "token_type": "bearer",
        },
    )

    return IssueJwtResponse(**res)


class ValidateJwtRequest(BaseModel):
    token: str
    audience: str | None = None


class ValidateJwtResponse(BaseModel):
    active: bool
    claims: dict[str, object] | None = None
    error: str | None = None


@router.post("/jwt/validate", response_model=ValidateJwtResponse)
async def validate_jwt_route(req: ValidateJwtRequest, request: Request):
    # RBAC: Require JWT_VALIDATE permission
    # Note: For validation, we don't need tenant isolation since we're just checking token validity
    user = await rbac_middleware.validate_request(request, Permission.JWT_VALIDATE)

    try:
        res = validate_jwt(req.token, req.audience)
        claims = res.get("claims", {})

        # Log successful JWT validation
        log_custom_event(
            event_type=AuditEventType.AUTH_TOKEN_VALIDATED,
            result=AuditResult.SUCCESS,
            actor_id=user.user_id,
            tenant_id=claims.get("tenant_id", "unknown"),
            action="validate_jwt",
            description="JWT token validated successfully",
            resource_type="auth",
            metadata={
                "subject": claims.get("sub"),
                "audience": req.audience,
                "issuer": claims.get("iss"),
                "expires_at": claims.get("exp"),
                "issued_at": claims.get("iat"),
            },
        )

        return ValidateJwtResponse(active=True, claims=claims)

    except Exception as e:
        # Log failed JWT validation
        log_custom_event(
            event_type=AuditEventType.AUTH_TOKEN_INVALID,
            result=AuditResult.FAILURE,
            actor_id=user.user_id,
            tenant_id="unknown",
            action="validate_jwt",
            description="JWT token validation failed",
            resource_type="auth",
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
                "audience": req.audience,
            },
        )

        return ValidateJwtResponse(active=False, error=str(e))


class OAuthTokenRequest(BaseModel):
    grant_type: str
    code: str | None = None
    code_verifier: str | None = None
    redirect_uri: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    scope: str | None = None
    audience: str | None = None
    subject_token: str | None = None
    subject_token_type: str | None = None


class OAuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: str | None = None
    id_token: str | None = None


@router.post("/oauth/token", response_model=OAuthTokenResponse)
async def oauth_token(req: OAuthTokenRequest, request: Request) -> OAuthTokenResponse:
    # RBAC: Require OAUTH_TOKEN permission
    user = await rbac_middleware.validate_request(request, Permission.OAUTH_TOKEN)

    # TODO: Implement actual OAuth2 flows
    return OAuthTokenResponse(access_token="stub-access", expires_in=3600)
