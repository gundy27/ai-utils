"""OAuth2 storage layer for clients, authorization codes, and tokens."""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import structlog

from .models import (
    AuthorizationCode,
    OAuth2Client,
    RefreshToken,
    PKCEChallenge,
)

logger = structlog.get_logger(__name__)


class InMemoryOAuth2Storage:
    """In-memory storage for OAuth2 clients, codes, and tokens."""

    def __init__(self, max_items: int = 10000):
        """Initialize the storage."""
        self.logger = logger.bind(component="oauth2_storage")
        self.max_items = max_items
        self._lock = threading.Lock()

        # Storage containers
        self._clients: Dict[str, OAuth2Client] = {}
        self._authorization_codes: Dict[str, AuthorizationCode] = {}
        self._refresh_tokens: Dict[str, RefreshToken] = {}
        self._pkce_challenges: Dict[str, PKCEChallenge] = {}

        self.logger.info(
            "oauth2_storage_initialized",
            max_items=max_items,
        )

    # Client management
    def store_client(self, client: OAuth2Client) -> None:
        """Store an OAuth2 client."""
        with self._lock:
            self._clients[client.client_id] = client
            self.logger.debug(
                "oauth2_client_stored",
                client_id=client.client_id,
                client_type=client.client_type,
                tenant_id=client.tenant_id,
            )

    def get_client(self, client_id: str) -> Optional[OAuth2Client]:
        """Get an OAuth2 client by ID."""
        with self._lock:
            client = self._clients.get(client_id)
            if client and not client.is_active:
                return None
            return client

    def list_clients(self, tenant_id: Optional[str] = None) -> List[OAuth2Client]:
        """List OAuth2 clients, optionally filtered by tenant."""
        with self._lock:
            clients = list(self._clients.values())

            if tenant_id:
                clients = [c for c in clients if c.tenant_id == tenant_id]

            # Only return active clients
            return [c for c in clients if c.is_active]

    def update_client(self, client_id: str, **updates) -> Optional[OAuth2Client]:
        """Update an OAuth2 client."""
        with self._lock:
            if client_id not in self._clients:
                return None

            client = self._clients[client_id]

            # Update fields
            for key, value in updates.items():
                if hasattr(client, key):
                    setattr(client, key, value)

            client.updated_at = datetime.utcnow()

            self.logger.debug(
                "oauth2_client_updated",
                client_id=client_id,
                updates=list(updates.keys()),
            )

            return client

    def delete_client(self, client_id: str) -> bool:
        """Delete an OAuth2 client."""
        with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
                self.logger.debug("oauth2_client_deleted", client_id=client_id)
                return True
            return False

    # Authorization code management
    def store_authorization_code(self, code: AuthorizationCode) -> None:
        """Store an authorization code."""
        with self._lock:
            self._authorization_codes[code.code] = code
            self._cleanup_expired_codes()

            self.logger.debug(
                "authorization_code_stored",
                code=code.code[:8] + "...",  # Log partial code for security
                client_id=code.client_id,
                user_id=code.user_id,
                tenant_id=code.tenant_id,
                expires_at=code.expires_at.isoformat(),
            )

    def get_authorization_code(self, code: str) -> Optional[AuthorizationCode]:
        """Get an authorization code."""
        with self._lock:
            auth_code = self._authorization_codes.get(code)
            if auth_code and auth_code.is_expired():
                # Remove expired code
                del self._authorization_codes[code]
                return None
            return auth_code

    def use_authorization_code(self, code: str) -> Optional[AuthorizationCode]:
        """Mark an authorization code as used."""
        with self._lock:
            auth_code = self._authorization_codes.get(code)
            if auth_code and not auth_code.is_expired() and not auth_code.is_used():
                auth_code.used_at = datetime.utcnow()

                self.logger.debug(
                    "authorization_code_used",
                    code=code[:8] + "...",
                    client_id=auth_code.client_id,
                    user_id=auth_code.user_id,
                )

                return auth_code
            return None

    def _cleanup_expired_codes(self) -> None:
        """Remove expired authorization codes."""
        now = datetime.utcnow()
        expired_codes = [
            code
            for code, auth_code in self._authorization_codes.items()
            if auth_code.expires_at < now
        ]

        for code in expired_codes:
            del self._authorization_codes[code]

        if expired_codes:
            self.logger.debug(
                "expired_authorization_codes_cleaned",
                count=len(expired_codes),
            )

    # Refresh token management
    def store_refresh_token(self, token: RefreshToken) -> None:
        """Store a refresh token."""
        with self._lock:
            self._refresh_tokens[token.refresh_token] = token
            self._cleanup_expired_refresh_tokens()

            self.logger.debug(
                "refresh_token_stored",
                token=token.refresh_token[:8] + "...",
                client_id=token.client_id,
                user_id=token.user_id,
                tenant_id=token.tenant_id,
                expires_at=token.expires_at.isoformat(),
            )

    def get_refresh_token(self, refresh_token: str) -> Optional[RefreshToken]:
        """Get a refresh token."""
        with self._lock:
            token = self._refresh_tokens.get(refresh_token)
            if token and token.is_expired():
                # Remove expired token
                del self._refresh_tokens[refresh_token]
                return None
            return token

    def use_refresh_token(self, refresh_token: str) -> Optional[RefreshToken]:
        """Mark a refresh token as used."""
        with self._lock:
            token = self._refresh_tokens.get(refresh_token)
            if token and not token.is_expired() and not token.is_used():
                token.used_at = datetime.utcnow()

                self.logger.debug(
                    "refresh_token_used",
                    token=refresh_token[:8] + "...",
                    client_id=token.client_id,
                    user_id=token.user_id,
                )

                return token
            return None

    def revoke_refresh_token(self, refresh_token: str) -> bool:
        """Revoke a refresh token."""
        with self._lock:
            if refresh_token in self._refresh_tokens:
                del self._refresh_tokens[refresh_token]
                self.logger.debug(
                    "refresh_token_revoked", token=refresh_token[:8] + "..."
                )
                return True
            return False

    def _cleanup_expired_refresh_tokens(self) -> None:
        """Remove expired refresh tokens."""
        now = datetime.utcnow()
        expired_tokens = [
            token
            for token, refresh_token in self._refresh_tokens.items()
            if refresh_token.expires_at < now
        ]

        for token in expired_tokens:
            del self._refresh_tokens[token]

        if expired_tokens:
            self.logger.debug(
                "expired_refresh_tokens_cleaned",
                count=len(expired_tokens),
            )

    # PKCE challenge management
    def store_pkce_challenge(
        self, code_challenge: str, challenge: PKCEChallenge
    ) -> None:
        """Store a PKCE challenge."""
        with self._lock:
            self._pkce_challenges[code_challenge] = challenge

            self.logger.debug(
                "pkce_challenge_stored",
                challenge=code_challenge[:8] + "...",
                method=challenge.code_challenge_method,
            )

    def get_pkce_challenge(self, code_challenge: str) -> Optional[PKCEChallenge]:
        """Get a PKCE challenge."""
        with self._lock:
            return self._pkce_challenges.get(code_challenge)

    def remove_pkce_challenge(self, code_challenge: str) -> bool:
        """Remove a PKCE challenge."""
        with self._lock:
            if code_challenge in self._pkce_challenges:
                del self._pkce_challenges[code_challenge]
                self.logger.debug(
                    "pkce_challenge_removed", challenge=code_challenge[:8] + "..."
                )
                return True
            return False

    # Cleanup and maintenance
    def cleanup_expired_items(self) -> None:
        """Clean up all expired items."""
        with self._lock:
            self._cleanup_expired_codes()
            self._cleanup_expired_refresh_tokens()

    def get_stats(self) -> Dict[str, int]:
        """Get storage statistics."""
        with self._lock:
            return {
                "clients": len(self._clients),
                "authorization_codes": len(self._authorization_codes),
                "refresh_tokens": len(self._refresh_tokens),
                "pkce_challenges": len(self._pkce_challenges),
            }

    def generate_client_id(self) -> str:
        """Generate a unique client ID."""
        import secrets

        return secrets.token_urlsafe(16)

    def generate_client_secret(self) -> str:
        """Generate a secure client secret."""
        import secrets

        return secrets.token_urlsafe(32)


# Global storage instance
oauth2_storage = InMemoryOAuth2Storage()
