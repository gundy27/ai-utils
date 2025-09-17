"""OAuth2 module for authorization and token flows."""

from .models import (
    AuthorizationRequest,
    AuthorizationCode,
    TokenRequest,
    TokenResponse,
    OAuth2Client,
    RefreshToken,
    AccessToken,
    PKCEChallenge,
    AuthorizationError,
    TokenError,
    OAuth2ErrorType,
    GrantType,
    ResponseType,
    CodeChallengeMethod,
    ClientType,
    build_authorization_url,
    create_authorization_error,
    create_token_error,
)
from .service import oauth2_service
from .storage import oauth2_storage, InMemoryOAuth2Storage

__all__ = [
    # Models
    "AuthorizationRequest",
    "AuthorizationCode",
    "TokenRequest",
    "TokenResponse",
    "OAuth2Client",
    "RefreshToken",
    "AccessToken",
    "PKCEChallenge",
    "AuthorizationError",
    "TokenError",
    "OAuth2ErrorType",
    "GrantType",
    "ResponseType",
    "CodeChallengeMethod",
    "ClientType",
    # Utility functions
    "build_authorization_url",
    "create_authorization_error",
    "create_token_error",
    # Service and storage
    "oauth2_service",
    "oauth2_storage",
    "InMemoryOAuth2Storage",
]
