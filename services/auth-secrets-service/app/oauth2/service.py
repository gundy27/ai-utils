"""OAuth2 service layer for handling authorization and token flows."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple

import structlog

from .models import (
    AuthorizationCode,
    AuthorizationRequest,
    AuthorizationError,
    TokenRequest,
    TokenResponse,
    TokenError,
    OAuth2Client,
    RefreshToken,
    AccessToken,
    PKCEChallenge,
    OAuth2ErrorType,
    GrantType,
    ResponseType,
)
from .storage import oauth2_storage

logger = structlog.get_logger(__name__)


class OAuth2Service:
    """OAuth2 service for handling authorization and token flows."""

    def __init__(self):
        """Initialize the OAuth2 service."""
        self.logger = logger.bind(component="oauth2_service")
        self.storage = oauth2_storage

        # Configuration
        self.authorization_code_ttl = 600  # 10 minutes
        self.access_token_ttl = 3600  # 1 hour
        self.refresh_token_ttl = 86400 * 30  # 30 days

        self.logger.info("oauth2_service_initialized")

    # Authorization flow
    def validate_authorization_request(
        self, request: AuthorizationRequest, user_id: str, tenant_id: str
    ) -> Tuple[bool, Optional[AuthorizationError]]:
        """Validate an authorization request."""
        try:
            # Get client
            client = self.storage.get_client(request.client_id)
            if not client:
                return False, AuthorizationError(
                    error=OAuth2ErrorType.INVALID_CLIENT.value,
                    error_description="Invalid client_id",
                    state=request.state,
                )

            # Validate redirect URI
            if request.redirect_uri not in client.redirect_uris:
                return False, AuthorizationError(
                    error=OAuth2ErrorType.INVALID_REQUEST.value,
                    error_description="Invalid redirect_uri",
                    state=request.state,
                )

            # Validate response type
            if request.response_type != ResponseType.CODE:
                return False, AuthorizationError(
                    error=OAuth2ErrorType.UNSUPPORTED_RESPONSE_TYPE.value,
                    error_description="Only 'code' response type is supported",
                    state=request.state,
                )

            # Validate scopes
            if request.scope:
                requested_scopes = set(request.scope.split())
                allowed_scopes = set(client.allowed_scopes)
                if not requested_scopes.issubset(allowed_scopes):
                    return False, AuthorizationError(
                        error=OAuth2ErrorType.INVALID_SCOPE.value,
                        error_description="Invalid scope",
                        state=request.state,
                    )

            # Validate PKCE parameters
            if client.client_type == "public" and not request.code_challenge:
                return False, AuthorizationError(
                    error=OAuth2ErrorType.INVALID_REQUEST.value,
                    error_description="PKCE code_challenge is required for public clients",
                    state=request.state,
                )

            return True, None

        except Exception as e:
            self.logger.error("authorization_request_validation_error", error=str(e))
            return False, AuthorizationError(
                error=OAuth2ErrorType.SERVER_ERROR.value,
                error_description="Internal server error",
                state=request.state,
            )

    def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        user_id: str,
        tenant_id: str,
        scopes: list[str],
        code_challenge: Optional[str] = None,
        code_challenge_method: Optional[str] = None,
    ) -> AuthorizationCode:
        """Create an authorization code."""
        expires_at = datetime.utcnow() + timedelta(seconds=self.authorization_code_ttl)

        auth_code = AuthorizationCode(
            code=AuthorizationCode.generate_code(),
            client_id=client_id,
            redirect_uri=redirect_uri,
            user_id=user_id,
            tenant_id=tenant_id,
            scopes=scopes,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            expires_at=expires_at,
        )

        self.storage.store_authorization_code(auth_code)

        self.logger.info(
            "authorization_code_created",
            client_id=client_id,
            user_id=user_id,
            tenant_id=tenant_id,
            scopes=scopes,
            expires_at=expires_at.isoformat(),
        )

        return auth_code

    # Token flow
    def validate_token_request(
        self, request: TokenRequest
    ) -> Tuple[bool, Optional[TokenError]]:
        """Validate a token request."""
        try:
            # Get client
            client = self.storage.get_client(request.client_id)
            if not client:
                return False, TokenError(
                    error=OAuth2ErrorType.INVALID_CLIENT.value,
                    error_description="Invalid client_id",
                )

            # Validate client secret for confidential clients
            if client.client_type == "confidential":
                if (
                    not request.client_secret
                    or request.client_secret != client.client_secret
                ):
                    return False, TokenError(
                        error=OAuth2ErrorType.INVALID_CLIENT.value,
                        error_description="Invalid client_secret",
                    )

            # Validate grant type
            if request.grant_type == GrantType.AUTHORIZATION_CODE:
                return self._validate_authorization_code_grant(request, client)
            elif request.grant_type == GrantType.REFRESH_TOKEN:
                return self._validate_refresh_token_grant(request, client)
            elif request.grant_type == GrantType.CLIENT_CREDENTIALS:
                return self._validate_client_credentials_grant(request, client)
            else:
                return False, TokenError(
                    error=OAuth2ErrorType.UNSUPPORTED_GRANT_TYPE.value,
                    error_description="Unsupported grant_type",
                )

        except Exception as e:
            self.logger.error("token_request_validation_error", error=str(e))
            return False, TokenError(
                error=OAuth2ErrorType.SERVER_ERROR.value,
                error_description="Internal server error",
            )

    def _validate_authorization_code_grant(
        self, request: TokenRequest, client: OAuth2Client
    ) -> Tuple[bool, Optional[TokenError]]:
        """Validate authorization code grant."""
        if not request.code:
            return False, TokenError(
                error=OAuth2ErrorType.INVALID_REQUEST.value,
                error_description="Missing code parameter",
            )

        if not request.redirect_uri:
            return False, TokenError(
                error=OAuth2ErrorType.INVALID_REQUEST.value,
                error_description="Missing redirect_uri parameter",
            )

        # Get authorization code
        auth_code = self.storage.get_authorization_code(request.code)
        if not auth_code:
            return False, TokenError(
                error=OAuth2ErrorType.INVALID_GRANT.value,
                error_description="Invalid or expired authorization code",
            )

        # Validate client ID
        if auth_code.client_id != client.client_id:
            return False, TokenError(
                error=OAuth2ErrorType.INVALID_GRANT.value,
                error_description="Authorization code was issued to a different client",
            )

        # Validate redirect URI
        if auth_code.redirect_uri != request.redirect_uri:
            return False, TokenError(
                error=OAuth2ErrorType.INVALID_GRANT.value,
                error_description="redirect_uri mismatch",
            )

        # Validate PKCE for public clients
        if client.client_type == "public":
            if not auth_code.code_challenge or not request.code_verifier:
                return False, TokenError(
                    error=OAuth2ErrorType.INVALID_REQUEST.value,
                    error_description="PKCE code_verifier is required for public clients",
                )

            # Verify PKCE challenge
            challenge = PKCEChallenge(
                code_challenge=auth_code.code_challenge,
                code_challenge_method=auth_code.code_challenge_method,
            )

            if not challenge.verify(request.code_verifier):
                return False, TokenError(
                    error=OAuth2ErrorType.INVALID_GRANT.value,
                    error_description="Invalid PKCE code_verifier",
                )

        return True, None

    def _validate_refresh_token_grant(
        self, request: TokenRequest, client: OAuth2Client
    ) -> Tuple[bool, Optional[TokenError]]:
        """Validate refresh token grant."""
        if not request.refresh_token:
            return False, TokenError(
                error=OAuth2ErrorType.INVALID_REQUEST.value,
                error_description="Missing refresh_token parameter",
            )

        # Get refresh token
        refresh_token = self.storage.get_refresh_token(request.refresh_token)
        if not refresh_token:
            return False, TokenError(
                error=OAuth2ErrorType.INVALID_GRANT.value,
                error_description="Invalid or expired refresh token",
            )

        # Validate client ID
        if refresh_token.client_id != client.client_id:
            return False, TokenError(
                error=OAuth2ErrorType.INVALID_GRANT.value,
                error_description="Refresh token was issued to a different client",
            )

        return True, None

    def _validate_client_credentials_grant(
        self, request: TokenRequest, client: OAuth2Client
    ) -> Tuple[bool, Optional[TokenError]]:
        """Validate client credentials grant."""
        # Client credentials grant is only for confidential clients
        if client.client_type != "confidential":
            return False, TokenError(
                error=OAuth2ErrorType.UNAUTHORIZED_CLIENT.value,
                error_description="Client credentials grant is only for confidential clients",
            )

        return True, None

    def exchange_code_for_token(
        self,
        code: str,
        redirect_uri: str,
        client_id: str,
        code_verifier: Optional[str] = None,
    ) -> TokenResponse:
        """Exchange authorization code for access token."""
        # Use the authorization code (mark as used)
        auth_code = self.storage.use_authorization_code(code)
        if not auth_code:
            raise ValueError("Invalid or expired authorization code")

        # Generate access token
        access_token = AccessToken.generate_access_token()
        expires_at = datetime.utcnow() + timedelta(seconds=self.access_token_ttl)

        # Generate refresh token
        refresh_token = None
        if auth_code.scopes:  # Only issue refresh tokens for scoped requests
            refresh_token_obj = RefreshToken(
                refresh_token=RefreshToken.generate_refresh_token(),
                client_id=client_id,
                user_id=auth_code.user_id,
                tenant_id=auth_code.tenant_id,
                scopes=auth_code.scopes,
                expires_at=datetime.utcnow()
                + timedelta(seconds=self.refresh_token_ttl),
            )

            self.storage.store_refresh_token(refresh_token_obj)
            refresh_token = refresh_token_obj.refresh_token

        self.logger.info(
            "access_token_issued",
            client_id=client_id,
            user_id=auth_code.user_id,
            tenant_id=auth_code.tenant_id,
            scopes=auth_code.scopes,
            expires_at=expires_at.isoformat(),
        )

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self.access_token_ttl,
            refresh_token=refresh_token,
            scope=" ".join(auth_code.scopes) if auth_code.scopes else None,
        )

    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh an access token using a refresh token."""
        # Use the refresh token (mark as used)
        refresh_token_obj = self.storage.use_refresh_token(refresh_token)
        if not refresh_token_obj:
            raise ValueError("Invalid or expired refresh token")

        # Generate new access token
        access_token = AccessToken.generate_access_token()

        # Optionally generate new refresh token (rotate)
        new_refresh_token = None
        if refresh_token_obj.scopes:
            new_refresh_token_obj = RefreshToken(
                refresh_token=RefreshToken.generate_refresh_token(),
                client_id=refresh_token_obj.client_id,
                user_id=refresh_token_obj.user_id,
                tenant_id=refresh_token_obj.tenant_id,
                scopes=refresh_token_obj.scopes,
                expires_at=datetime.utcnow()
                + timedelta(seconds=self.refresh_token_ttl),
            )

            self.storage.store_refresh_token(new_refresh_token_obj)
            new_refresh_token = new_refresh_token_obj.refresh_token

        self.logger.info(
            "access_token_refreshed",
            client_id=refresh_token_obj.client_id,
            user_id=refresh_token_obj.user_id,
            tenant_id=refresh_token_obj.tenant_id,
            scopes=refresh_token_obj.scopes,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self.access_token_ttl,
            refresh_token=new_refresh_token,
            scope=(
                " ".join(refresh_token_obj.scopes) if refresh_token_obj.scopes else None
            ),
        )

    def issue_client_credentials_token(
        self, client_id: str, scopes: list[str]
    ) -> TokenResponse:
        """Issue access token for client credentials grant."""
        # Generate access token
        access_token = AccessToken.generate_access_token()

        self.logger.info(
            "client_credentials_token_issued",
            client_id=client_id,
            scopes=scopes,
        )

        return TokenResponse(
            access_token=access_token,
            token_type="Bearer",
            expires_in=self.access_token_ttl,
            scope=" ".join(scopes) if scopes else None,
        )

    def revoke_token(self, token: str, token_type_hint: Optional[str] = None) -> bool:
        """Revoke a token (access token or refresh token)."""
        # Try refresh token first
        if self.storage.revoke_refresh_token(token):
            self.logger.info("refresh_token_revoked", token=token[:8] + "...")
            return True

        # For access tokens, we'd need to implement a blacklist
        # For now, we'll just log the attempt
        self.logger.info("access_token_revoke_attempted", token=token[:8] + "...")
        return True  # Always return True for access tokens


# Global service instance
oauth2_service = OAuth2Service()
