"""OAuth2 data models and schemas."""

from __future__ import annotations

import secrets
import hashlib
import base64
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlencode

from pydantic import BaseModel, Field, field_validator


class GrantType(str, Enum):
    """OAuth2 grant types."""

    AUTHORIZATION_CODE = "authorization_code"
    CLIENT_CREDENTIALS = "client_credentials"
    REFRESH_TOKEN = "refresh_token"


class ResponseType(str, Enum):
    """OAuth2 response types."""

    CODE = "code"


class CodeChallengeMethod(str, Enum):
    """PKCE code challenge methods."""

    S256 = "S256"
    PLAIN = "plain"


class ClientType(str, Enum):
    """OAuth2 client types."""

    PUBLIC = "public"  # Cannot keep client secrets (mobile, SPA)
    CONFIDENTIAL = "confidential"  # Can keep client secrets (server-side apps)


class OAuth2Client(BaseModel):
    """OAuth2 client configuration."""

    client_id: str
    client_secret: Optional[str] = None
    client_type: ClientType
    name: str
    description: Optional[str] = None
    redirect_uris: list[str] = Field(default_factory=list)
    allowed_scopes: list[str] = Field(default_factory=list)
    tenant_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

    @field_validator("client_secret")
    @classmethod
    def validate_client_secret(cls, v, info):
        """Validate client secret based on client type."""
        if info.data and "client_type" in info.data:
            if info.data["client_type"] == ClientType.CONFIDENTIAL and not v:
                raise ValueError("Confidential clients must have a client_secret")
            if info.data["client_type"] == ClientType.PUBLIC and v:
                raise ValueError("Public clients cannot have a client_secret")
        return v

    @field_validator("redirect_uris")
    @classmethod
    def validate_redirect_uris(cls, v):
        """Validate redirect URIs."""
        if not v:
            raise ValueError("At least one redirect URI is required")

        # Basic URI validation
        for uri in v:
            if not uri.startswith(("http://", "https://", "urn:ietf:wg:oauth:2.0:oob")):
                raise ValueError(f"Invalid redirect URI: {uri}")

        return v


class AuthorizationRequest(BaseModel):
    """OAuth2 authorization request."""

    client_id: str
    redirect_uri: str
    response_type: ResponseType = ResponseType.CODE
    scope: Optional[str] = None
    state: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: CodeChallengeMethod = CodeChallengeMethod.S256

    @field_validator("response_type")
    @classmethod
    def validate_response_type(cls, v):
        """Only support authorization code flow."""
        if v != ResponseType.CODE:
            raise ValueError("Only 'code' response type is supported")
        return v

    @field_validator("code_challenge_method")
    @classmethod
    def validate_code_challenge_method(cls, v):
        """Only support S256 method for PKCE."""
        if v != CodeChallengeMethod.S256:
            raise ValueError("Only 'S256' code challenge method is supported")
        return v


class AuthorizationCode(BaseModel):
    """OAuth2 authorization code."""

    code: str
    client_id: str
    redirect_uri: str
    user_id: str
    tenant_id: str
    scopes: list[str]
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[CodeChallengeMethod] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = None

    @classmethod
    def generate_code(cls) -> str:
        """Generate a secure authorization code."""
        return secrets.token_urlsafe(32)

    def is_expired(self) -> bool:
        """Check if the authorization code is expired."""
        return datetime.utcnow() > self.expires_at

    def is_used(self) -> bool:
        """Check if the authorization code has been used."""
        return self.used_at is not None


class TokenRequest(BaseModel):
    """OAuth2 token request."""

    grant_type: GrantType
    code: Optional[str] = None
    redirect_uri: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class AccessToken(BaseModel):
    """OAuth2 access token."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None

    @classmethod
    def generate_access_token(cls, expires_in: int = 3600) -> str:
        """Generate a secure access token."""
        return secrets.token_urlsafe(32)


class RefreshToken(BaseModel):
    """OAuth2 refresh token."""

    refresh_token: str
    client_id: str
    user_id: str
    tenant_id: str
    scopes: list[str]
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    used_at: Optional[datetime] = None

    @classmethod
    def generate_refresh_token(cls) -> str:
        """Generate a secure refresh token."""
        return secrets.token_urlsafe(32)

    def is_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return datetime.utcnow() > self.expires_at

    def is_used(self) -> bool:
        """Check if the refresh token has been used."""
        return self.used_at is not None


class TokenResponse(BaseModel):
    """OAuth2 token response."""

    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class PKCEChallenge(BaseModel):
    """PKCE code challenge and verifier."""

    code_verifier: str
    code_challenge: str
    code_challenge_method: CodeChallengeMethod = CodeChallengeMethod.S256

    @classmethod
    def generate(cls) -> PKCEChallenge:
        """Generate a new PKCE challenge."""
        # Generate code verifier (43-128 characters)
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("ascii")
            .rstrip("=")
        )

        # Generate code challenge using S256
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("ascii")).digest()
            )
            .decode("ascii")
            .rstrip("=")
        )

        return cls(
            code_verifier=code_verifier,
            code_challenge=code_challenge,
            code_challenge_method=CodeChallengeMethod.S256,
        )

    def verify(self, code_verifier: str) -> bool:
        """Verify a code verifier against the challenge."""
        if self.code_challenge_method == CodeChallengeMethod.S256:
            expected_challenge = (
                base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode("ascii")).digest()
                )
                .decode("ascii")
                .rstrip("=")
            )
            return self.code_challenge == expected_challenge
        elif self.code_challenge_method == CodeChallengeMethod.PLAIN:
            return self.code_challenge == code_verifier
        else:
            return False


class AuthorizationError(BaseModel):
    """OAuth2 authorization error."""

    error: str
    error_description: Optional[str] = None
    error_uri: Optional[str] = None
    state: Optional[str] = None


class TokenError(BaseModel):
    """OAuth2 token error."""

    error: str
    error_description: Optional[str] = None
    error_uri: Optional[str] = None


def build_authorization_url(
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    state: Optional[str] = None,
    code_challenge: Optional[str] = None,
    code_challenge_method: CodeChallengeMethod = CodeChallengeMethod.S256,
    auth_endpoint: str = "/auth/oauth/authorize",
) -> str:
    """Build an OAuth2 authorization URL."""
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes) if scopes else "",
    }

    if state:
        params["state"] = state

    if code_challenge:
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = code_challenge_method.value

    # Remove empty values
    params = {k: v for k, v in params.items() if v}

    return f"{auth_endpoint}?{urlencode(params)}"


# OAuth2 error types
class OAuth2ErrorType(str, Enum):
    """OAuth2 error types."""

    INVALID_REQUEST = "invalid_request"
    INVALID_CLIENT = "invalid_client"
    INVALID_GRANT = "invalid_grant"
    UNAUTHORIZED_CLIENT = "unauthorized_client"
    UNSUPPORTED_GRANT_TYPE = "unsupported_grant_type"
    INVALID_SCOPE = "invalid_scope"
    ACCESS_DENIED = "access_denied"
    SERVER_ERROR = "server_error"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"


def create_authorization_error(
    error: OAuth2ErrorType,
    description: Optional[str] = None,
    uri: Optional[str] = None,
    state: Optional[str] = None,
) -> AuthorizationError:
    """Create an OAuth2 authorization error."""
    return AuthorizationError(
        error=error.value, error_description=description, error_uri=uri, state=state
    )


def create_token_error(
    error: OAuth2ErrorType, description: Optional[str] = None, uri: Optional[str] = None
) -> TokenError:
    """Create an OAuth2 token error."""
    return TokenError(error=error.value, error_description=description, error_uri=uri)
