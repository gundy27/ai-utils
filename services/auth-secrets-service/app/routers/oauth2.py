"""OAuth2 API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException, Query, Form
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional

from ..oauth2.models import (
    AuthorizationRequest,
    AuthorizationError,
    TokenRequest,
    TokenResponse,
    TokenError,
    OAuth2Client,
    PKCEChallenge,
    ClientType,
    build_authorization_url,
    create_authorization_error,
    create_token_error,
    OAuth2ErrorType,
    GrantType,
)
from ..oauth2.service import oauth2_service
from ..oauth2.storage import oauth2_storage
from ..rbac import rbac_middleware, Permission
from ..audit import log_custom_event, AuditEventType, AuditResult
from ..errors import error_response

router = APIRouter(prefix="/oauth2", tags=["oauth2"])


# Client management endpoints
class ClientRegistrationRequest(BaseModel):
    """OAuth2 client registration request."""

    name: str
    description: Optional[str] = None
    client_type: str  # "public" or "confidential"
    redirect_uris: list[str]
    allowed_scopes: list[str] = []


class ClientRegistrationResponse(BaseModel):
    """OAuth2 client registration response."""

    client_id: str
    client_secret: Optional[str] = None
    client_type: str
    name: str
    description: Optional[str] = None
    redirect_uris: list[str]
    allowed_scopes: list[str]
    tenant_id: str


@router.post("/clients", response_model=ClientRegistrationResponse)
async def register_client(req: ClientRegistrationRequest, request: Request):
    """Register a new OAuth2 client."""
    # RBAC: Require CLIENT_MANAGE permission
    user = await rbac_middleware.validate_request(
        request,
        Permission.CLIENT_MANAGE,
        None,  # Will be set from user's tenant
    )

    try:
        # Generate client credentials
        client_id = f"client_{oauth2_service.storage.generate_client_id()}"
        client_secret = None

        if req.client_type == "confidential":
            client_secret = oauth2_service.storage.generate_client_secret()

        # Create client
        client = OAuth2Client(
            client_id=client_id,
            client_secret=client_secret,
            client_type=ClientType(req.client_type),
            name=req.name,
            description=req.description,
            redirect_uris=req.redirect_uris,
            allowed_scopes=req.allowed_scopes,
            tenant_id=user.tenant_id,
        )

        oauth2_storage.store_client(client)

        # Log successful client registration
        log_custom_event(
            event_type=AuditEventType.CLIENT_REGISTERED,
            result=AuditResult.SUCCESS,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            action="register_client",
            description=f"Registered OAuth2 client: {client.name}",
            resource_type="oauth2_client",
            resource_id=client_id,
            metadata={
                "client_type": req.client_type,
                "redirect_uris": req.redirect_uris,
                "allowed_scopes": req.allowed_scopes,
            },
        )

        return ClientRegistrationResponse(
            client_id=client.client_id,
            client_secret=client.client_secret,
            client_type=client.client_type,
            name=client.name,
            description=client.description,
            redirect_uris=client.redirect_uris,
            allowed_scopes=client.allowed_scopes,
            tenant_id=client.tenant_id,
        )

    except Exception as e:
        # Log failed client registration
        log_custom_event(
            event_type=AuditEventType.CLIENT_REGISTRATION_FAILED,
            result=AuditResult.FAILURE,
            actor_id=user.user_id,
            tenant_id=user.tenant_id,
            action="register_client",
            description=f"Failed to register OAuth2 client: {req.name}",
            resource_type="oauth2_client",
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise


@router.get("/clients", response_model=list[ClientRegistrationResponse])
async def list_clients(request: Request, tenant_id: Optional[str] = Query(None)):
    """List OAuth2 clients."""
    # RBAC: Require CLIENT_READ permission
    user = await rbac_middleware.validate_request(
        request, Permission.CLIENT_READ, tenant_id or user.tenant_id
    )

    clients = oauth2_storage.list_clients(tenant_id or user.tenant_id)

    return [
        ClientRegistrationResponse(
            client_id=client.client_id,
            client_secret=None,  # Never return secrets in list
            client_type=client.client_type,
            name=client.name,
            description=client.description,
            redirect_uris=client.redirect_uris,
            allowed_scopes=client.allowed_scopes,
            tenant_id=client.tenant_id,
        )
        for client in clients
    ]


# Authorization endpoints
@router.get("/authorize")
async def authorize(
    client_id: str = Query(...),
    redirect_uri: str = Query(...),
    response_type: str = Query("code"),
    scope: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    code_challenge: Optional[str] = Query(None),
    code_challenge_method: str = Query("S256"),
    request: Request = None,
):
    """OAuth2 authorization endpoint."""
    try:
        # Parse authorization request
        auth_request = AuthorizationRequest(
            client_id=client_id,
            redirect_uri=redirect_uri,
            response_type=response_type,
            scope=scope,
            state=state,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        # For now, we'll simulate user authentication
        # In a real implementation, this would redirect to a login page
        # and the user would authenticate before being redirected back

        # Get client to determine tenant
        client = oauth2_storage.get_client(client_id)
        if not client:
            error_url = build_error_url(
                redirect_uri, OAuth2ErrorType.INVALID_CLIENT, "Invalid client_id", state
            )
            return RedirectResponse(url=error_url)

        # Validate request
        is_valid, error = oauth2_service.validate_authorization_request(
            auth_request,
            user_id="demo-user",  # In real implementation, get from session
            tenant_id=client.tenant_id,
        )

        if not is_valid:
            error_url = build_error_url(
                redirect_uri,
                OAuth2ErrorType(error.error),
                error.error_description,
                state,
            )
            return RedirectResponse(url=error_url)

        # Parse scopes
        scopes = []
        if auth_request.scope:
            scopes = auth_request.scope.split()

        # Create authorization code
        auth_code = oauth2_service.create_authorization_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            user_id="demo-user",  # In real implementation, get from session
            tenant_id=client.tenant_id,
            scopes=scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
        )

        # Log successful authorization
        log_custom_event(
            event_type=AuditEventType.AUTHORIZATION_GRANTED,
            result=AuditResult.SUCCESS,
            actor_id="demo-user",
            tenant_id=client.tenant_id,
            action="authorize",
            description=f"Granted authorization to client {client.name}",
            resource_type="oauth2_client",
            resource_id=client_id,
            metadata={
                "scopes": scopes,
                "redirect_uri": redirect_uri,
                "has_pkce": bool(code_challenge),
            },
        )

        # Build success redirect URL
        success_url = build_success_url(redirect_uri, auth_code.code, state)
        return RedirectResponse(url=success_url)

    except Exception as e:
        # Log authorization error
        log_custom_event(
            event_type=AuditEventType.AUTHORIZATION_FAILED,
            result=AuditResult.FAILURE,
            actor_id="demo-user",
            tenant_id=(
                getattr(client, "tenant_id", "unknown")
                if "client" in locals()
                else "unknown"
            ),
            action="authorize",
            description=f"Failed authorization request",
            resource_type="oauth2_client",
            resource_id=client_id,
            metadata={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        error_url = build_error_url(
            redirect_uri, OAuth2ErrorType.SERVER_ERROR, "Internal server error", state
        )
        return RedirectResponse(url=error_url)


# Token endpoints
class TokenRequestForm(BaseModel):
    """Token request form data."""

    grant_type: str
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


@router.post("/token", response_model=TokenResponse)
async def token_endpoint(
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    redirect_uri: Optional[str] = Form(None),
    client_id: Optional[str] = Form(None),
    client_secret: Optional[str] = Form(None),
    code_verifier: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None),
    scope: Optional[str] = Form(None),
):
    """OAuth2 token endpoint."""
    try:
        # Parse token request
        token_request = TokenRequest(
            grant_type=grant_type,
            code=code,
            redirect_uri=redirect_uri,
            client_id=client_id,
            client_secret=client_secret,
            code_verifier=code_verifier,
            refresh_token=refresh_token,
            scope=scope,
        )

        # Validate request
        is_valid, error = oauth2_service.validate_token_request(token_request)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error.dict())

        # Exchange for token based on grant type
        if token_request.grant_type == GrantType.AUTHORIZATION_CODE:
            token_response = oauth2_service.exchange_code_for_token(
                code=token_request.code,
                redirect_uri=token_request.redirect_uri,
                client_id=token_request.client_id,
                code_verifier=token_request.code_verifier,
            )
        elif token_request.grant_type == GrantType.REFRESH_TOKEN:
            token_response = oauth2_service.refresh_access_token(
                refresh_token=token_request.refresh_token
            )
        elif token_request.grant_type == GrantType.CLIENT_CREDENTIALS:
            scopes = []
            if token_request.scope:
                scopes = token_request.scope.split()
            token_response = oauth2_service.issue_client_credentials_token(
                client_id=token_request.client_id, scopes=scopes
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=create_token_error(
                    OAuth2ErrorType.UNSUPPORTED_GRANT_TYPE, "Unsupported grant_type"
                ).dict(),
            )

        # Log successful token issuance
        log_custom_event(
            event_type=AuditEventType.TOKEN_ISSUED,
            result=AuditResult.SUCCESS,
            actor_id="system",
            tenant_id="system",
            action="issue_token",
            description=f"Issued token via {grant_type} grant",
            resource_type="oauth2_token",
            metadata={
                "grant_type": grant_type,
                "client_id": client_id,
                "has_refresh_token": bool(token_response.refresh_token),
                "expires_in": token_response.expires_in,
            },
        )

        return token_response

    except HTTPException:
        raise
    except Exception as e:
        # Log token issuance error
        log_custom_event(
            event_type=AuditEventType.TOKEN_ISSUANCE_FAILED,
            result=AuditResult.FAILURE,
            actor_id="system",
            tenant_id="system",
            action="issue_token",
            description=f"Failed to issue token via {grant_type} grant",
            resource_type="oauth2_token",
            metadata={
                "grant_type": grant_type,
                "client_id": client_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

        raise HTTPException(
            status_code=500,
            detail=create_token_error(
                OAuth2ErrorType.SERVER_ERROR, "Internal server error"
            ).dict(),
        )


# PKCE helper endpoint
@router.get("/pkce/challenge", response_model=dict)
async def generate_pkce_challenge():
    """Generate a PKCE challenge for public clients."""
    challenge = PKCEChallenge.generate()

    return {
        "code_verifier": challenge.code_verifier,
        "code_challenge": challenge.code_challenge,
        "code_challenge_method": challenge.code_challenge_method,
    }


# Utility functions
def build_success_url(redirect_uri: str, code: str, state: Optional[str] = None) -> str:
    """Build success redirect URL with authorization code."""
    from urllib.parse import urlencode

    params = {"code": code}
    if state:
        params["state"] = state

    return f"{redirect_uri}?{urlencode(params)}"


def build_error_url(
    redirect_uri: str,
    error: OAuth2ErrorType,
    description: Optional[str] = None,
    state: Optional[str] = None,
) -> str:
    """Build error redirect URL."""
    from urllib.parse import urlencode

    params = {"error": error.value}
    if description:
        params["error_description"] = description
    if state:
        params["state"] = state

    return f"{redirect_uri}?{urlencode(params)}"
