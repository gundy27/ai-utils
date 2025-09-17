"""Tests for RBAC functionality."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.rbac.models import Permission, Role, User, create_user_from_jwt_claims


class TestRBACModels:
    """Test RBAC data models."""

    def test_user_permissions(self):
        """Test user permission checking."""
        user = User(
            user_id="test-user",
            tenant_id="tenant-1",
            roles=[Role.TENANT_ADMIN],
            permissions=[Permission.SECRET_READ, Permission.SECRET_WRITE],
        )

        assert user.has_permission(Permission.SECRET_READ)
        assert user.has_permission(Permission.SECRET_WRITE)
        assert not user.has_permission(Permission.SECRET_DELETE)

    def test_user_tenant_access(self):
        """Test tenant access control."""
        user = User(
            user_id="test-user",
            tenant_id="tenant-1",
            roles=[Role.TENANT_USER],
            permissions=[Permission.SECRET_READ],
        )

        assert user.can_access_tenant("tenant-1")
        assert not user.can_access_tenant("tenant-2")

    def test_system_admin_tenant_access(self):
        """Test system admin can access any tenant."""
        user = User(
            user_id="admin-user",
            tenant_id="tenant-1",
            roles=[Role.SYSTEM_ADMIN],
            permissions=[],
        )

        assert user.can_access_tenant("tenant-1")
        assert user.can_access_tenant("tenant-2")
        assert user.can_access_tenant("any-tenant")

    def test_create_user_from_jwt_claims(self):
        """Test creating user from JWT claims."""
        claims = {
            "sub": "test-user",
            "tenant_id": "tenant-1",
            "roles": ["tenant_admin"],
        }

        user = create_user_from_jwt_claims(claims)
        assert user is not None
        assert user.user_id == "test-user"
        assert user.tenant_id == "tenant-1"
        assert Role.TENANT_ADMIN in user.roles
        assert Permission.SECRET_READ in user.permissions

    def test_create_user_invalid_claims(self):
        """Test creating user with invalid JWT claims."""
        # Missing required fields
        claims = {"sub": "test-user"}
        user = create_user_from_jwt_claims(claims)
        assert user is None

        # Invalid role
        claims = {
            "sub": "test-user",
            "tenant_id": "tenant-1",
            "roles": ["invalid_role"],
        }
        user = create_user_from_jwt_claims(claims)
        assert user is not None
        assert user.roles == []  # Invalid role ignored


class TestRBACIntegration:
    """Test RBAC integration with API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_secrets_fetch_without_auth(self):
        """Test that secrets fetch requires authentication."""
        response = self.client.post(
            "/secrets/fetch",
            json={
                "tenant_id": "tenant-1",
                "scope": "prod",
                "name": "API_KEY",
            },
        )
        assert response.status_code == 401

    def test_secrets_rotate_without_auth(self):
        """Test that secrets rotate requires authentication."""
        response = self.client.post(
            "/secrets/rotate",
            json={
                "tenant_id": "tenant-1",
                "scope": "prod",
                "name": "API_KEY",
            },
        )
        assert response.status_code == 401

    def test_auth_jwt_issue_without_auth(self):
        """Test that JWT issue requires authentication."""
        response = self.client.post(
            "/auth/jwt/issue",
            json={
                "subject": "test-user",
                "tenant_id": "tenant-1",
                "scopes": ["read"],
                "audience": "test-audience",
                "ttl_s": 3600,
            },
        )
        assert response.status_code == 401

    def test_auth_jwt_validate_without_auth(self):
        """Test that JWT validate requires authentication."""
        response = self.client.post(
            "/auth/jwt/validate",
            json={
                "token": "invalid-token",
            },
        )
        assert response.status_code == 401

    def test_audit_logs_without_auth(self):
        """Test that audit logs require authentication."""
        response = self.client.get("/audit/logs", params={"tenant_id": "tenant-1"})
        assert response.status_code == 401


class TestRolePermissions:
    """Test role-to-permissions mapping."""

    def test_tenant_admin_permissions(self):
        """Test tenant admin has correct permissions."""
        from app.rbac.models import ROLE_PERMISSIONS

        permissions = ROLE_PERMISSIONS[Role.TENANT_ADMIN]
        assert Permission.SECRET_READ in permissions
        assert Permission.SECRET_WRITE in permissions
        assert Permission.SECRET_ROTATE in permissions
        assert Permission.JWT_ISSUE in permissions
        assert Permission.USER_MANAGE in permissions

    def test_tenant_user_permissions(self):
        """Test tenant user has correct permissions."""
        from app.rbac.models import ROLE_PERMISSIONS

        permissions = ROLE_PERMISSIONS[Role.TENANT_USER]
        assert Permission.SECRET_READ in permissions
        assert Permission.SECRET_WRITE in permissions
        assert Permission.SECRET_ROTATE not in permissions
        assert Permission.USER_MANAGE not in permissions

    def test_tenant_readonly_permissions(self):
        """Test tenant readonly has correct permissions."""
        from app.rbac.models import ROLE_PERMISSIONS

        permissions = ROLE_PERMISSIONS[Role.TENANT_READONLY]
        assert Permission.SECRET_READ in permissions
        assert Permission.SECRET_WRITE not in permissions
        assert Permission.SECRET_ROTATE not in permissions

    def test_system_admin_permissions(self):
        """Test system admin has all permissions."""
        from app.rbac.models import ROLE_PERMISSIONS

        permissions = ROLE_PERMISSIONS[Role.SYSTEM_ADMIN]
        assert Permission.SECRET_READ in permissions
        assert Permission.SECRET_WRITE in permissions
        assert Permission.SECRET_ROTATE in permissions
        assert Permission.SECRET_DELETE in permissions
        assert Permission.SYSTEM_ADMIN in permissions


if __name__ == "__main__":
    pytest.main([__file__])
