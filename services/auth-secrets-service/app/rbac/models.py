from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class Permission(str, Enum):
    """Available permissions in the system."""

    # Secret permissions
    SECRET_READ = "secret:read"
    SECRET_WRITE = "secret:write"
    SECRET_ROTATE = "secret:rotate"
    SECRET_DELETE = "secret:delete"

    # Auth permissions
    JWT_ISSUE = "jwt:issue"
    JWT_VALIDATE = "jwt:validate"
    OAUTH_TOKEN = "oauth:token"

    # OAuth2 permissions
    CLIENT_READ = "client:read"
    CLIENT_WRITE = "client:write"
    CLIENT_MANAGE = "client:manage"

    # Token exchange permissions
    DELEGATE_TOKEN = "delegate:token"
    IMPERSONATE_USER = "impersonate:user"
    DELEGATION_POLICY_READ = "delegation_policy:read"
    DELEGATION_POLICY_WRITE = "delegation_policy:write"
    DELEGATION_POLICY_MANAGE = "delegation_policy:manage"

    # Audit permissions
    AUDIT_READ = "audit:read"
    AUDIT_WRITE = "audit:write"

    # Admin permissions
    TENANT_MANAGE = "tenant:manage"
    USER_MANAGE = "user:manage"
    SYSTEM_ADMIN = "system:admin"


class Role(str, Enum):
    """Predefined roles with their permissions."""

    # Tenant roles
    TENANT_ADMIN = "tenant_admin"
    TENANT_USER = "tenant_user"
    TENANT_READONLY = "tenant_readonly"

    # System roles
    SYSTEM_ADMIN = "system_admin"
    SERVICE_ACCOUNT = "service_account"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, List[Permission]] = {
    Role.TENANT_ADMIN: [
        Permission.SECRET_READ,
        Permission.SECRET_WRITE,
        Permission.SECRET_ROTATE,
        Permission.JWT_ISSUE,
        Permission.JWT_VALIDATE,
        Permission.CLIENT_READ,
        Permission.CLIENT_WRITE,
        Permission.CLIENT_MANAGE,
        Permission.DELEGATE_TOKEN,
        Permission.DELEGATION_POLICY_READ,
        Permission.DELEGATION_POLICY_WRITE,
        Permission.DELEGATION_POLICY_MANAGE,
        Permission.AUDIT_READ,
        Permission.USER_MANAGE,
    ],
    Role.TENANT_USER: [
        Permission.SECRET_READ,
        Permission.SECRET_WRITE,
        Permission.JWT_VALIDATE,
        Permission.CLIENT_READ,
        Permission.AUDIT_READ,
    ],
    Role.TENANT_READONLY: [
        Permission.SECRET_READ,
        Permission.JWT_VALIDATE,
        Permission.AUDIT_READ,
    ],
    Role.SYSTEM_ADMIN: [
        Permission.SECRET_READ,
        Permission.SECRET_WRITE,
        Permission.SECRET_ROTATE,
        Permission.SECRET_DELETE,
        Permission.JWT_ISSUE,
        Permission.JWT_VALIDATE,
        Permission.OAUTH_TOKEN,
        Permission.CLIENT_READ,
        Permission.CLIENT_WRITE,
        Permission.CLIENT_MANAGE,
        Permission.DELEGATE_TOKEN,
        Permission.IMPERSONATE_USER,
        Permission.DELEGATION_POLICY_READ,
        Permission.DELEGATION_POLICY_WRITE,
        Permission.DELEGATION_POLICY_MANAGE,
        Permission.AUDIT_READ,
        Permission.AUDIT_WRITE,
        Permission.TENANT_MANAGE,
        Permission.USER_MANAGE,
        Permission.SYSTEM_ADMIN,
    ],
    Role.SERVICE_ACCOUNT: [
        Permission.SECRET_READ,
        Permission.JWT_VALIDATE,
        Permission.AUDIT_READ,
    ],
}


class User(BaseModel):
    """User model with RBAC information."""

    user_id: str
    tenant_id: str
    roles: List[Role]
    permissions: List[Permission]
    is_active: bool = True

    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self.permissions

    def has_role(self, role: Role) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def can_access_tenant(self, tenant_id: str) -> bool:
        """Check if user can access a specific tenant."""
        # System admins can access any tenant
        if Role.SYSTEM_ADMIN in self.roles:
            return True
        # Regular users can only access their own tenant
        return self.tenant_id == tenant_id

    def get_effective_permissions(self, target_tenant_id: str) -> List[Permission]:
        """Get effective permissions for a specific tenant."""
        if not self.can_access_tenant(target_tenant_id):
            return []
        return self.permissions


class Tenant(BaseModel):
    """Tenant model for multi-tenancy."""

    tenant_id: str
    name: str
    is_active: bool = True
    created_at: Optional[str] = None
    settings: Dict[str, str] = {}


def create_user_from_jwt_claims(claims: Dict[str, object]) -> Optional[User]:
    """Create a User object from JWT claims."""
    try:
        user_id = str(claims.get("sub", ""))
        tenant_id = str(claims.get("tenant_id", ""))
        roles_str = claims.get("roles", [])

        if not user_id or not tenant_id:
            return None

        # Parse roles from claims
        roles = []
        if isinstance(roles_str, list):
            roles = [
                Role(role) for role in roles_str if role in Role.__members__.values()
            ]

        # Get permissions from roles
        permissions = []
        for role in roles:
            permissions.extend(ROLE_PERMISSIONS.get(role, []))

        # Remove duplicates
        permissions = list(set(permissions))

        return User(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
            permissions=permissions,
        )
    except (ValueError, TypeError) as e:
        # Invalid role or missing required fields
        return None


def get_permissions_for_role(role: Role) -> List[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])
