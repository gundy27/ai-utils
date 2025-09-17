"""Tests for OAuth2 implementation."""

import pytest
import secrets
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from app.oauth2.models import (
    AuthorizationRequest,
    AuthorizationCode,
    TokenRequest,
    TokenResponse,
    OAuth2Client,
    RefreshToken,
    PKCEChallenge,
    AuthorizationError,
    TokenError,
    OAuth2ErrorType,
    GrantType,
    ResponseType,
    CodeChallengeMethod,
    ClientType,
)
from app.oauth2.service import OAuth2Service
from app.oauth2.storage import InMemoryOAuth2Storage


class TestOAuth2Models:
    """Test OAuth2 data models."""

    def test_oauth2_client_creation(self):
        """Test OAuth2 client creation and validation."""
        # Confidential client with secret
        client = OAuth2Client(
            client_id="test-client",
            client_secret="secret123",
            client_type=ClientType.CONFIDENTIAL,
            name="Test Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["read", "write"],
            tenant_id="tenant-1",
        )

        assert client.client_id == "test-client"
        assert client.client_secret == "secret123"
        assert client.client_type == ClientType.CONFIDENTIAL
        assert client.redirect_uris == ["https://example.com/callback"]
        assert client.is_active is True

    def test_oauth2_client_validation(self):
        """Test OAuth2 client validation rules."""
        # Test valid public client (no secret)
        public_client = OAuth2Client(
            client_id="public-client",
            client_secret=None,  # No secret for public client
            client_type=ClientType.PUBLIC,
            name="Public Client",
            redirect_uris=["https://example.com/callback"],
            tenant_id="tenant-1",
        )
        assert public_client.client_type == ClientType.PUBLIC
        assert public_client.client_secret is None

        # Test valid confidential client (with secret)
        confidential_client = OAuth2Client(
            client_id="confidential-client",
            client_secret="secret123",
            client_type=ClientType.CONFIDENTIAL,
            name="Confidential Client",
            redirect_uris=["https://example.com/callback"],
            tenant_id="tenant-1",
        )
        assert confidential_client.client_type == ClientType.CONFIDENTIAL
        assert confidential_client.client_secret == "secret123"

        # Must have at least one redirect URI
        with pytest.raises(Exception):  # Pydantic validation error
            OAuth2Client(
                client_id="test-client",
                client_type=ClientType.PUBLIC,
                name="Test Client",
                redirect_uris=[],
                tenant_id="tenant-1",
            )

    def test_authorization_request_validation(self):
        """Test authorization request validation."""
        # Valid request
        request = AuthorizationRequest(
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            response_type=ResponseType.CODE,
            scope="read write",
            state="random-state",
            code_challenge="challenge123",
            code_challenge_method=CodeChallengeMethod.S256,
        )

        assert request.client_id == "test-client"
        assert request.response_type == ResponseType.CODE

        # Invalid response type
        with pytest.raises(Exception):  # Pydantic validation error
            AuthorizationRequest(
                client_id="test-client",
                redirect_uri="https://example.com/callback",
                response_type="token",  # Invalid
            )

    def test_authorization_code_lifecycle(self):
        """Test authorization code lifecycle."""
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        code = AuthorizationCode(
            code="auth-code-123",
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read", "write"],
            expires_at=expires_at,
        )

        assert not code.is_expired()
        assert not code.is_used()

        # Mark as used
        code.used_at = datetime.utcnow()
        assert code.is_used()

    def test_pkce_challenge_generation(self):
        """Test PKCE challenge generation and verification."""
        challenge = PKCEChallenge.generate()

        assert challenge.code_challenge_method == CodeChallengeMethod.S256
        assert len(challenge.code_verifier) > 40  # Should be 43+ characters
        assert len(challenge.code_challenge) == 43  # Base64 URL-safe without padding

        # Verify the challenge
        assert challenge.verify(challenge.code_verifier)
        assert not challenge.verify("wrong-verifier")


class TestOAuth2Storage:
    """Test OAuth2 storage layer."""

    def setup_method(self):
        """Set up test storage."""
        self.storage = InMemoryOAuth2Storage()

    def test_client_storage(self):
        """Test client storage operations."""
        client = OAuth2Client(
            client_id="test-client",
            client_type=ClientType.PUBLIC,
            name="Test Client",
            redirect_uris=["https://example.com/callback"],
            tenant_id="tenant-1",
        )

        # Store client
        self.storage.store_client(client)

        # Retrieve client
        retrieved = self.storage.get_client("test-client")
        assert retrieved is not None
        assert retrieved.client_id == "test-client"
        assert retrieved.name == "Test Client"

        # List clients
        clients = self.storage.list_clients("tenant-1")
        assert len(clients) == 1
        assert clients[0].client_id == "test-client"

        # Update client
        updated = self.storage.update_client("test-client", name="Updated Client")
        assert updated.name == "Updated Client"

        # Delete client
        deleted = self.storage.delete_client("test-client")
        assert deleted is True

        # Verify deletion
        assert self.storage.get_client("test-client") is None

    def test_authorization_code_storage(self):
        """Test authorization code storage."""
        expires_at = datetime.utcnow() + timedelta(minutes=10)

        auth_code = AuthorizationCode(
            code="auth-code-123",
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read"],
            expires_at=expires_at,
        )

        # Store code
        self.storage.store_authorization_code(auth_code)

        # Retrieve code
        retrieved = self.storage.get_authorization_code("auth-code-123")
        assert retrieved is not None
        assert retrieved.code == "auth-code-123"

        # Use code
        used_code = self.storage.use_authorization_code("auth-code-123")
        assert used_code is not None
        assert used_code.used_at is not None

        # Try to use again (should fail)
        used_again = self.storage.use_authorization_code("auth-code-123")
        assert used_again is None

    def test_refresh_token_storage(self):
        """Test refresh token storage."""
        expires_at = datetime.utcnow() + timedelta(days=30)

        refresh_token = RefreshToken(
            refresh_token="refresh-token-123",
            client_id="test-client",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read"],
            expires_at=expires_at,
        )

        # Store token
        self.storage.store_refresh_token(refresh_token)

        # Retrieve token
        retrieved = self.storage.get_refresh_token("refresh-token-123")
        assert retrieved is not None
        assert retrieved.refresh_token == "refresh-token-123"

        # Use token
        used_token = self.storage.use_refresh_token("refresh-token-123")
        assert used_token is not None
        assert used_token.used_at is not None

        # Revoke token
        revoked = self.storage.revoke_refresh_token("refresh-token-123")
        assert revoked is True

        # Verify revocation
        assert self.storage.get_refresh_token("refresh-token-123") is None


class TestOAuth2Service:
    """Test OAuth2 service layer."""

    def setup_method(self):
        """Set up test service."""
        self.storage = InMemoryOAuth2Storage()
        self.service = OAuth2Service()
        self.service.storage = self.storage

        # Create test client
        self.client = OAuth2Client(
            client_id="test-client",
            client_type=ClientType.CONFIDENTIAL,
            client_secret="client-secret",
            name="Test Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["read", "write"],
            tenant_id="tenant-1",
        )
        self.storage.store_client(self.client)

    def test_authorization_request_validation_success(self):
        """Test successful authorization request validation."""
        request = AuthorizationRequest(
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            response_type=ResponseType.CODE,
            scope="read",
        )

        is_valid, error = self.service.validate_authorization_request(
            request, "user-123", "tenant-1"
        )

        assert is_valid is True
        assert error is None

    def test_authorization_request_validation_failure(self):
        """Test failed authorization request validation."""
        # Invalid client
        request = AuthorizationRequest(
            client_id="invalid-client",
            redirect_uri="https://example.com/callback",
            response_type=ResponseType.CODE,
        )

        is_valid, error = self.service.validate_authorization_request(
            request, "user-123", "tenant-1"
        )

        assert is_valid is False
        assert error.error == OAuth2ErrorType.INVALID_CLIENT.value

        # Invalid redirect URI
        request = AuthorizationRequest(
            client_id="test-client",
            redirect_uri="https://evil.com/callback",
            response_type=ResponseType.CODE,
        )

        is_valid, error = self.service.validate_authorization_request(
            request, "user-123", "tenant-1"
        )

        assert is_valid is False
        assert error.error == OAuth2ErrorType.INVALID_REQUEST.value

    def test_create_authorization_code(self):
        """Test authorization code creation."""
        auth_code = self.service.create_authorization_code(
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read"],
        )

        assert auth_code.client_id == "test-client"
        assert auth_code.user_id == "user-123"
        assert auth_code.scopes == ["read"]
        assert not auth_code.is_expired()

        # Verify stored in storage
        stored = self.storage.get_authorization_code(auth_code.code)
        assert stored is not None

    def test_token_request_validation(self):
        """Test token request validation."""
        # Create authorization code first
        auth_code = AuthorizationCode(
            code="auth-code-123",
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read"],
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        self.storage.store_authorization_code(auth_code)

        # Valid authorization code request
        request = TokenRequest(
            grant_type=GrantType.AUTHORIZATION_CODE,
            code="auth-code-123",
            redirect_uri="https://example.com/callback",
            client_id="test-client",
            client_secret="client-secret",
        )

        is_valid, error = self.service.validate_token_request(request)
        assert is_valid is True
        assert error is None

        # Invalid client secret
        request.client_secret = "wrong-secret"
        is_valid, error = self.service.validate_token_request(request)
        assert is_valid is False
        assert error.error == OAuth2ErrorType.INVALID_CLIENT.value

    def test_exchange_code_for_token(self):
        """Test authorization code to token exchange."""
        # Create and store authorization code
        auth_code = AuthorizationCode(
            code="auth-code-123",
            client_id="test-client",
            redirect_uri="https://example.com/callback",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read"],
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        self.storage.store_authorization_code(auth_code)

        # Exchange for token
        token_response = self.service.exchange_code_for_token(
            code="auth-code-123",
            redirect_uri="https://example.com/callback",
            client_id="test-client",
        )

        assert token_response.access_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.expires_in == 3600
        assert token_response.refresh_token is not None
        assert token_response.scope == "read"

        # Verify code is marked as used
        used_code = self.storage.get_authorization_code("auth-code-123")
        assert used_code.used_at is not None

    def test_refresh_token_flow(self):
        """Test refresh token flow."""
        # Create and store refresh token
        refresh_token = RefreshToken(
            refresh_token="refresh-token-123",
            client_id="test-client",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read"],
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        self.storage.store_refresh_token(refresh_token)

        # Refresh access token
        token_response = self.service.refresh_access_token("refresh-token-123")

        assert token_response.access_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.refresh_token is not None  # New refresh token
        assert token_response.scope == "read"

        # Verify old refresh token is marked as used
        used_token = self.storage.get_refresh_token("refresh-token-123")
        assert used_token.used_at is not None

    def test_client_credentials_grant(self):
        """Test client credentials grant."""
        # Create confidential client
        confidential_client = OAuth2Client(
            client_id="confidential-client",
            client_type=ClientType.CONFIDENTIAL,
            client_secret="client-secret",
            name="Confidential Client",
            redirect_uris=["https://example.com/callback"],  # Required for validation
            allowed_scopes=["read"],
            tenant_id="tenant-1",
        )
        self.storage.store_client(confidential_client)

        # Issue client credentials token
        token_response = self.service.issue_client_credentials_token(
            client_id="confidential-client", scopes=["read"]
        )

        assert token_response.access_token is not None
        assert token_response.token_type == "Bearer"
        assert token_response.scope == "read"
        assert (
            token_response.refresh_token is None
        )  # No refresh token for client credentials


class TestOAuth2Integration:
    """Test OAuth2 integration scenarios."""

    def setup_method(self):
        """Set up integration test."""
        self.storage = InMemoryOAuth2Storage()
        self.service = OAuth2Service()
        self.service.storage = self.storage

    def test_full_authorization_code_flow(self):
        """Test complete authorization code flow with PKCE."""
        # 1. Register public client
        public_client = OAuth2Client(
            client_id="public-client",
            client_type=ClientType.PUBLIC,
            name="Public Client",
            redirect_uris=["https://example.com/callback"],
            allowed_scopes=["read"],
            tenant_id="tenant-1",
        )
        self.storage.store_client(public_client)

        # 2. Generate PKCE challenge
        pkce_challenge = PKCEChallenge.generate()

        # 3. Validate authorization request
        auth_request = AuthorizationRequest(
            client_id="public-client",
            redirect_uri="https://example.com/callback",
            response_type=ResponseType.CODE,
            scope="read",
            code_challenge=pkce_challenge.code_challenge,
            code_challenge_method=CodeChallengeMethod.S256,
        )

        is_valid, error = self.service.validate_authorization_request(
            auth_request, "user-123", "tenant-1"
        )
        assert is_valid is True

        # 4. Create authorization code
        auth_code = self.service.create_authorization_code(
            client_id="public-client",
            redirect_uri="https://example.com/callback",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read"],
            code_challenge=pkce_challenge.code_challenge,
            code_challenge_method=CodeChallengeMethod.S256,
        )

        # 5. Exchange code for token
        token_response = self.service.exchange_code_for_token(
            code=auth_code.code,
            redirect_uri="https://example.com/callback",
            client_id="public-client",
            code_verifier=pkce_challenge.code_verifier,
        )

        assert token_response.access_token is not None
        assert token_response.refresh_token is not None

    def test_token_revocation(self):
        """Test token revocation."""
        # Create refresh token
        refresh_token = RefreshToken(
            refresh_token="refresh-token-123",
            client_id="test-client",
            user_id="user-123",
            tenant_id="tenant-1",
            scopes=["read"],
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        self.storage.store_refresh_token(refresh_token)

        # Revoke token
        revoked = self.service.revoke_token("refresh-token-123")
        assert revoked is True

        # Verify token is gone
        assert self.storage.get_refresh_token("refresh-token-123") is None


if __name__ == "__main__":
    pytest.main([__file__])
