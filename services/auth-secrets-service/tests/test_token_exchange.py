"""Test suite for token exchange functionality."""

import pytest
import jwt
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from app.token_exchange.models import (
    TokenExchangeRequest,
    TokenExchangeResponse,
    TokenExchangeError,
    DelegationRequest,
    DelegationResponse,
    ImpersonationRequest,
    ImpersonationResponse,
    DelegationPolicy,
    TokenExchangeErrorType,
    SubjectTokenType,
    RequestedTokenType,
    create_token_exchange_error,
    validate_delegation_chain,
    build_delegation_audit_event,
)
from app.token_exchange.service import TokenExchangeService
from app.token_exchange.storage import InMemoryTokenExchangeStorage
from app.rbac.models import Role


class TestTokenExchangeModels:
    """Test token exchange data models."""

    def test_token_exchange_request_validation(self):
        """Test token exchange request validation."""
        # Valid request
        request = TokenExchangeRequest(
            subject_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
            subject_token_type=SubjectTokenType.ACCESS_TOKEN,
            requested_token_type=RequestedTokenType.ACCESS_TOKEN,
            audience="api.example.com",
            scope="read write",
        )

        assert request.grant_type == "urn:ietf:params:oauth:grant-type:token-exchange"
        assert request.subject_token_type == SubjectTokenType.ACCESS_TOKEN
        assert request.requested_token_type == RequestedTokenType.ACCESS_TOKEN
        assert request.audience == "api.example.com"
        assert request.scope == "read write"

    def test_token_exchange_request_invalid_grant_type(self):
        """Test token exchange request with invalid grant type."""
        with pytest.raises(Exception):  # Pydantic validation error
            TokenExchangeRequest(
                grant_type="invalid_grant_type",
                subject_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                subject_token_type=SubjectTokenType.ACCESS_TOKEN,
            )

    def test_delegation_request(self):
        """Test delegation request model."""
        request = DelegationRequest(
            source_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
            target_audience="microservice.example.com",
            target_scopes=["read", "write"],
            impersonation=False,
            delegation_chain=["token1", "token2"],
            expires_in=3600,
        )

        assert request.source_token.startswith("eyJ")
        assert request.target_audience == "microservice.example.com"
        assert request.target_scopes == ["read", "write"]
        assert request.impersonation is False
        assert len(request.delegation_chain) == 2
        assert request.expires_in == 3600

    def test_impersonation_request(self):
        """Test impersonation request model."""
        request = ImpersonationRequest(
            source_token="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
            target_user_id="user123",
            target_tenant_id="tenant456",
            impersonation_reason="Admin support request",
            target_scopes=["admin:read", "admin:write"],
            expires_in=1800,
        )

        assert request.source_token.startswith("eyJ")
        assert request.target_user_id == "user123"
        assert request.target_tenant_id == "tenant456"
        assert request.impersonation_reason == "Admin support request"
        assert request.target_scopes == ["admin:read", "admin:write"]
        assert request.expires_in == 1800

    def test_delegation_policy(self):
        """Test delegation policy model."""
        policy = DelegationPolicy(
            policy_id="policy123",
            name="Microservice Delegation",
            description="Allow microservice token delegation",
            source_scopes=["read", "write"],
            target_scopes=["read"],
            allowed_audiences=["microservice.example.com"],
            max_delegation_depth=3,
            requires_impersonation_permission=False,
            tenant_id="tenant123",
        )

        assert policy.policy_id == "policy123"
        assert policy.name == "Microservice Delegation"
        assert policy.source_scopes == ["read", "write"]
        assert policy.target_scopes == ["read"]
        assert policy.max_delegation_depth == 3
        assert policy.requires_impersonation_permission is False

    def test_validate_delegation_chain(self):
        """Test delegation chain validation."""
        # Valid chain
        valid_chain = ["token1", "token2", "token3"]
        assert validate_delegation_chain(valid_chain, max_depth=5) is True

        # Chain too long
        long_chain = ["token1", "token2", "token3", "token4", "token5", "token6"]
        assert validate_delegation_chain(long_chain, max_depth=5) is False

        # Chain with cycles
        cyclic_chain = ["token1", "token2", "token1"]
        assert validate_delegation_chain(cyclic_chain, max_depth=5) is False

        # Empty chain
        assert validate_delegation_chain([], max_depth=5) is True

    def test_build_delegation_audit_event(self):
        """Test building delegation audit event."""
        event = build_delegation_audit_event(
            event_type="token_exchange",
            actor_id="user123",
            tenant_id="tenant456",
            source_token="token123",
            target_token="token456",
            source_scopes=["read", "write"],
            target_scopes=["read"],
            success=True,
            audience="api.example.com",
        )

        assert event.event_type == "token_exchange"
        assert event.actor_id == "user123"
        assert event.tenant_id == "tenant456"
        assert event.source_scopes == ["read", "write"]
        assert event.target_scopes == ["read"]
        assert event.success is True
        assert event.audience == "api.example.com"


class TestTokenExchangeStorage:
    """Test token exchange storage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryTokenExchangeStorage(max_events=1000)

    def test_store_and_get_delegation_policy(self):
        """Test storing and retrieving delegation policies."""
        policy = DelegationPolicy(
            policy_id="policy123",
            name="Test Policy",
            tenant_id="tenant123",
            source_scopes=["read"],
            target_scopes=["read"],
        )

        self.storage.store_delegation_policy(policy)
        retrieved = self.storage.get_delegation_policy("policy123")

        assert retrieved is not None
        assert retrieved.policy_id == "policy123"
        assert retrieved.name == "Test Policy"
        assert retrieved.source_scopes == ["read"]

    def test_list_delegation_policies(self):
        """Test listing delegation policies."""
        policy1 = DelegationPolicy(
            policy_id="policy1", name="Policy 1", tenant_id="tenant1"
        )
        policy2 = DelegationPolicy(
            policy_id="policy2", name="Policy 2", tenant_id="tenant2"
        )

        self.storage.store_delegation_policy(policy1)
        self.storage.store_delegation_policy(policy2)

        # List all policies
        all_policies = self.storage.list_delegation_policies()
        assert len(all_policies) == 2

        # List policies for specific tenant
        tenant1_policies = self.storage.list_delegation_policies("tenant1")
        assert len(tenant1_policies) == 1
        assert tenant1_policies[0].policy_id == "policy1"

    def test_find_matching_policy(self):
        """Test finding matching delegation policy."""
        policy = DelegationPolicy(
            policy_id="policy123",
            name="Test Policy",
            tenant_id="tenant123",
            source_scopes=["read", "write"],
            target_scopes=["read"],
            allowed_audiences=["api.example.com"],
        )

        self.storage.store_delegation_policy(policy)

        # Find matching policy
        matching = self.storage.find_matching_policy(
            source_scopes=["read", "write"],
            target_scopes=["read"],
            audience="api.example.com",
            tenant_id="tenant123",
        )

        assert matching is not None
        assert matching.policy_id == "policy123"

        # No matching policy for different scopes
        no_match = self.storage.find_matching_policy(
            source_scopes=["admin"],
            target_scopes=["read"],
            audience="api.example.com",
            tenant_id="tenant123",
        )

        assert no_match is None

    def test_store_and_query_audit_events(self):
        """Test storing and querying audit events."""
        from app.token_exchange.models import TokenExchangeAuditEvent

        event1 = TokenExchangeAuditEvent(
            event_id="event1",
            event_type="token_exchange",
            actor_id="user1",
            tenant_id="tenant1",
            source_token_type="access_token",
            target_token_type="access_token",
            source_scopes=["read"],
            target_scopes=["read"],
            success=True,
        )

        event2 = TokenExchangeAuditEvent(
            event_id="event2",
            event_type="token_delegation",
            actor_id="user2",
            tenant_id="tenant2",
            source_token_type="access_token",
            target_token_type="access_token",
            source_scopes=["write"],
            target_scopes=["read"],
            success=False,
        )

        self.storage.store_audit_event(event1)
        self.storage.store_audit_event(event2)

        # Query all events
        all_events = self.storage.query_audit_events()
        assert len(all_events) == 2

        # Query by tenant
        tenant1_events = self.storage.query_audit_events(tenant_id="tenant1")
        assert len(tenant1_events) == 1
        assert tenant1_events[0].event_id == "event1"

        # Query by success status
        successful_events = self.storage.query_audit_events(success=True)
        assert len(successful_events) == 1
        assert successful_events[0].event_id == "event1"

    def test_audit_stats(self):
        """Test audit statistics."""
        from app.token_exchange.models import TokenExchangeAuditEvent

        # Create test events
        events = [
            TokenExchangeAuditEvent(
                event_id=f"event{i}",
                event_type="token_exchange" if i % 2 == 0 else "token_delegation",
                actor_id=f"user{i}",
                tenant_id="tenant1",
                source_token_type="access_token",
                target_token_type="access_token",
                source_scopes=["read"],
                target_scopes=["read"],
                success=i % 2 == 0,
            )
            for i in range(5)
        ]

        for event in events:
            self.storage.store_audit_event(event)

        stats = self.storage.get_audit_stats("tenant1")

        assert stats["total_events"] == 5
        assert stats["successful_exchanges"] == 3  # events 0, 2, 4
        assert stats["failed_exchanges"] == 2  # events 1, 3
        assert stats["delegation_events"] == 2  # events 1, 3
        assert stats["impersonation_events"] == 0


class TestTokenExchangeService:
    """Test token exchange service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TokenExchangeService()
        self.mock_storage = InMemoryTokenExchangeStorage()
        self.service.storage = self.mock_storage

    @patch("app.token_exchange.service.validate_jwt")
    @patch("app.token_exchange.service.issue_jwt")
    def test_exchange_token_success(self, mock_issue_jwt, mock_validate_jwt):
        """Test successful token exchange."""
        # Mock JWT validation
        mock_validate_jwt.return_value = {
            "active": True,
            "claims": {
                "sub": "user123",
                "tenant_id": "tenant456",
                "scope": "read write",
                "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            },
        }

        # Mock JWT issuance
        mock_issue_jwt.return_value = {
            "access_token": "new_access_token_123",
            "expires_in": 3600,
        }

        # Create delegation policy
        policy = DelegationPolicy(
            policy_id="policy123",
            name="Test Policy",
            tenant_id="tenant456",
            source_scopes=["read", "write"],
            target_scopes=["read"],
        )
        self.mock_storage.store_delegation_policy(policy)

        # Create token exchange request
        request = TokenExchangeRequest(
            subject_token="valid_token",
            subject_token_type=SubjectTokenType.ACCESS_TOKEN,
            requested_token_type=RequestedTokenType.ACCESS_TOKEN,
            scope="read",
        )

        # Exchange token
        response = self.service.exchange_token(request, "client123")

        assert isinstance(response, TokenExchangeResponse)
        assert response.access_token == "new_access_token_123"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
        assert response.scope == "read"

    @patch("app.token_exchange.service.validate_jwt")
    def test_exchange_token_invalid_token(self, mock_validate_jwt):
        """Test token exchange with invalid token."""
        # Mock JWT validation failure
        mock_validate_jwt.return_value = {"active": False}

        request = TokenExchangeRequest(
            subject_token="invalid_token",
            subject_token_type=SubjectTokenType.ACCESS_TOKEN,
            requested_token_type=RequestedTokenType.ACCESS_TOKEN,
        )

        with pytest.raises(ValueError, match="Token exchange validation failed"):
            self.service.exchange_token(request, "client123")

    @patch("app.token_exchange.service.validate_jwt")
    @patch("app.token_exchange.service.issue_jwt")
    def test_delegate_token_success(self, mock_issue_jwt, mock_validate_jwt):
        """Test successful token delegation."""
        # Mock JWT validation
        mock_validate_jwt.return_value = {
            "active": True,
            "claims": {
                "sub": "user123",
                "tenant_id": "tenant456",
                "scope": "read write",
                "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            },
        }

        # Mock JWT issuance
        mock_issue_jwt.return_value = {
            "access_token": "delegated_token_123",
            "expires_in": 3600,
        }

        # Create delegation policy
        policy = DelegationPolicy(
            policy_id="policy123",
            name="Test Policy",
            tenant_id="tenant456",
            source_scopes=["read", "write"],
            target_scopes=["read"],
            allowed_audiences=["microservice.example.com"],
            max_delegation_depth=3,
        )
        self.mock_storage.store_delegation_policy(policy)

        # Create delegation request
        request = DelegationRequest(
            source_token="valid_token",
            target_audience="microservice.example.com",
            target_scopes=["read"],
            delegation_chain=["token1", "token2"],
            expires_in=3600,
        )

        # Delegate token
        response = self.service.delegate_token(request, "client123")

        assert isinstance(response, DelegationResponse)
        assert response.delegated_token == "delegated_token_123"
        assert response.token_type == "Bearer"
        assert response.expires_in == 3600
        assert response.scope == "read"
        assert response.audience == "microservice.example.com"
        assert len(response.delegation_chain) == 3  # original + new token

    def test_delegate_token_chain_too_long(self):
        """Test token delegation with delegation chain too long."""
        request = DelegationRequest(
            source_token="valid_token",
            target_audience="microservice.example.com",
            target_scopes=["read"],
            delegation_chain=[
                "token1",
                "token2",
                "token3",
                "token4",
                "token5",
                "token6",
            ],
            expires_in=3600,
        )

        with pytest.raises(ValueError, match="Delegation chain too long"):
            self.service.delegate_token(request, "client123")

    @patch("app.token_exchange.service.validate_jwt")
    @patch("app.token_exchange.service.issue_jwt")
    def test_impersonate_user_success(self, mock_issue_jwt, mock_validate_jwt):
        """Test successful user impersonation."""
        # Mock JWT validation with admin role
        mock_validate_jwt.return_value = {
            "active": True,
            "claims": {
                "sub": "admin123",
                "tenant_id": "tenant456",
                "scope": "admin:read admin:write",
                "roles": ["system_admin"],
                "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            },
        }

        # Mock JWT issuance
        mock_issue_jwt.return_value = {
            "access_token": "impersonation_token_123",
            "expires_in": 1800,
        }

        # Create delegation policy for impersonation
        policy = DelegationPolicy(
            policy_id="policy123",
            name="Impersonation Policy",
            tenant_id="tenant456",
            source_scopes=["admin:read", "admin:write"],
            target_scopes=["admin:read"],
            requires_impersonation_permission=True,
        )
        self.mock_storage.store_delegation_policy(policy)

        # Create impersonation request
        request = ImpersonationRequest(
            source_token="admin_token",
            target_user_id="user123",
            target_tenant_id="tenant456",
            impersonation_reason="Admin support",
            target_scopes=["admin:read"],
            expires_in=1800,
        )

        # Impersonate user
        response = self.service.impersonate_user(request, "client123")

        assert isinstance(response, ImpersonationResponse)
        assert response.impersonation_token == "impersonation_token_123"
        assert response.token_type == "Bearer"
        assert response.expires_in == 1800
        assert response.scope == "admin:read"
        assert response.impersonated_user_id == "user123"
        assert response.impersonated_tenant_id == "tenant456"
        assert response.impersonation_reason == "Admin support"

    def test_impersonate_user_insufficient_permissions(self):
        """Test user impersonation with insufficient permissions."""
        with patch("app.token_exchange.service.validate_jwt") as mock_validate_jwt:
            # Mock JWT validation with non-admin role
            mock_validate_jwt.return_value = {
                "active": True,
                "claims": {
                    "sub": "user123",
                    "tenant_id": "tenant456",
                    "scope": "read write",
                    "roles": ["tenant_user"],
                    "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
                },
            }

            request = ImpersonationRequest(
                source_token="user_token",
                target_user_id="user456",
                target_scopes=["read"],
            )

            with pytest.raises(ValueError, match="Insufficient permissions"):
                self.service.impersonate_user(request, "client123")

    def test_create_delegation_policy(self):
        """Test creating delegation policy."""
        policy = self.service.create_delegation_policy(
            policy_id="policy123",
            name="Test Policy",
            tenant_id="tenant456",
            source_scopes=["read", "write"],
            target_scopes=["read"],
            allowed_audiences=["api.example.com"],
            max_delegation_depth=3,
        )

        assert policy.policy_id == "policy123"
        assert policy.name == "Test Policy"
        assert policy.tenant_id == "tenant456"
        assert policy.source_scopes == ["read", "write"]
        assert policy.target_scopes == ["read"]
        assert policy.allowed_audiences == ["api.example.com"]
        assert policy.max_delegation_depth == 3

        # Verify it's stored
        stored = self.mock_storage.get_delegation_policy("policy123")
        assert stored is not None
        assert stored.policy_id == "policy123"


class TestTokenExchangeIntegration:
    """Integration tests for token exchange."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = InMemoryTokenExchangeStorage()
        self.service = TokenExchangeService()
        self.service.storage = self.storage

    def test_end_to_end_delegation_flow(self):
        """Test end-to-end delegation flow."""
        # Create delegation policy
        policy = DelegationPolicy(
            policy_id="policy123",
            name="Microservice Delegation",
            tenant_id="tenant123",
            source_scopes=["read", "write"],
            target_scopes=["read"],
            allowed_audiences=["microservice.example.com"],
            max_delegation_depth=3,
        )
        self.storage.store_delegation_policy(policy)

        # Verify policy is stored and can be found
        stored_policy = self.storage.get_delegation_policy("policy123")
        assert stored_policy is not None

        matching_policy = self.storage.find_matching_policy(
            source_scopes=["read", "write"],
            target_scopes=["read"],
            audience="microservice.example.com",
            tenant_id="tenant123",
        )
        assert matching_policy is not None
        assert matching_policy.policy_id == "policy123"

    def test_audit_event_creation(self):
        """Test audit event creation and storage."""
        from app.token_exchange.models import TokenExchangeAuditEvent

        # Create audit event
        event = build_delegation_audit_event(
            event_type="token_exchange",
            actor_id="user123",
            tenant_id="tenant456",
            source_token="source_token",
            target_token="target_token",
            source_scopes=["read", "write"],
            target_scopes=["read"],
            success=True,
            audience="api.example.com",
        )

        # Store event
        self.storage.store_audit_event(event)

        # Query events
        events = self.storage.query_audit_events(tenant_id="tenant456")
        assert len(events) == 1

        stored_event = events[0]
        assert stored_event.event_type == "token_exchange"
        assert stored_event.actor_id == "user123"
        assert stored_event.tenant_id == "tenant456"
        assert stored_event.success is True
        assert stored_event.audience == "api.example.com"

        # Get stats
        stats = self.storage.get_audit_stats("tenant456")
        assert stats["total_events"] == 1
        assert stats["successful_exchanges"] == 1
        assert stats["failed_exchanges"] == 0
