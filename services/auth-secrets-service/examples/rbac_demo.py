#!/usr/bin/env python3
"""Demo script showing RBAC functionality."""

import json
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rbac.models import Permission, Role, User, create_user_from_jwt_claims


def demo_rbac_models():
    """Demonstrate RBAC model functionality."""
    print("=== RBAC Models Demo ===\n")

    # Create a tenant admin user
    admin_user = User(
        user_id="admin-123",
        tenant_id="acme-corp",
        roles=[Role.TENANT_ADMIN],
        permissions=[
            Permission.SECRET_READ,
            Permission.SECRET_WRITE,
            Permission.SECRET_ROTATE,
            Permission.JWT_ISSUE,
            Permission.USER_MANAGE,
        ],
    )

    print(f"Admin User: {admin_user.user_id}")
    print(f"Tenant: {admin_user.tenant_id}")
    print(f"Roles: {[role.value for role in admin_user.roles]}")
    print(f"Permissions: {[perm.value for perm in admin_user.permissions]}")

    # Test permission checks
    print(f"\nCan read secrets: {admin_user.has_permission(Permission.SECRET_READ)}")
    print(f"Can delete secrets: {admin_user.has_permission(Permission.SECRET_DELETE)}")
    print(f"Can manage users: {admin_user.has_permission(Permission.USER_MANAGE)}")

    # Test tenant access
    print(f"\nCan access own tenant: {admin_user.can_access_tenant('acme-corp')}")
    print(f"Can access other tenant: {admin_user.can_access_tenant('competitor-corp')}")

    print("\n" + "=" * 50 + "\n")

    # Create a regular user
    regular_user = User(
        user_id="user-456",
        tenant_id="acme-corp",
        roles=[Role.TENANT_USER],
        permissions=[
            Permission.SECRET_READ,
            Permission.SECRET_WRITE,
        ],
    )

    print(f"Regular User: {regular_user.user_id}")
    print(f"Tenant: {regular_user.tenant_id}")
    print(f"Roles: {[role.value for role in regular_user.roles]}")
    print(f"Permissions: {[perm.value for perm in regular_user.permissions]}")

    # Test permission checks
    print(f"\nCan read secrets: {regular_user.has_permission(Permission.SECRET_READ)}")
    print(
        f"Can rotate secrets: {regular_user.has_permission(Permission.SECRET_ROTATE)}"
    )
    print(f"Can issue JWTs: {regular_user.has_permission(Permission.JWT_ISSUE)}")

    # Test tenant access
    print(f"\nCan access own tenant: {regular_user.can_access_tenant('acme-corp')}")
    print(
        f"Can access other tenant: {regular_user.can_access_tenant('competitor-corp')}"
    )

    print("\n" + "=" * 50 + "\n")

    # Create a system admin
    system_admin = User(
        user_id="sys-admin",
        tenant_id="system",
        roles=[Role.SYSTEM_ADMIN],
        permissions=[],  # Will be populated from role
    )

    # Add permissions from role
    from app.rbac.models import ROLE_PERMISSIONS

    system_admin.permissions = ROLE_PERMISSIONS[Role.SYSTEM_ADMIN]

    print(f"System Admin: {system_admin.user_id}")
    print(f"Tenant: {system_admin.tenant_id}")
    print(f"Roles: {[role.value for role in system_admin.roles]}")
    print(f"Permission count: {len(system_admin.permissions)}")

    # Test tenant access (system admin can access any tenant)
    print(f"\nCan access acme-corp: {system_admin.can_access_tenant('acme-corp')}")
    print(
        f"Can access competitor-corp: {system_admin.can_access_tenant('competitor-corp')}"
    )
    print(f"Can access any tenant: {system_admin.can_access_tenant('any-tenant')}")


def demo_jwt_claims():
    """Demonstrate JWT claims to User conversion."""
    print("=== JWT Claims to User Demo ===\n")

    # Simulate JWT claims for a tenant admin
    jwt_claims = {
        "sub": "user-789",
        "tenant_id": "demo-tenant",
        "roles": ["tenant_admin"],
        "iat": 1234567890,
        "exp": 1234571490,
        "aud": "auth-service",
    }

    print("JWT Claims:")
    print(json.dumps(jwt_claims, indent=2))

    # Convert to User object
    user = create_user_from_jwt_claims(jwt_claims)

    if user:
        print(f"\nConverted User:")
        print(f"  User ID: {user.user_id}")
        print(f"  Tenant ID: {user.tenant_id}")
        print(f"  Roles: {[role.value for role in user.roles]}")
        print(f"  Permissions: {[perm.value for perm in user.permissions]}")
        print(f"  Is Active: {user.is_active}")
    else:
        print("\nFailed to create user from JWT claims")

    print("\n" + "=" * 50 + "\n")

    # Simulate JWT claims for a system admin
    system_jwt_claims = {
        "sub": "system-user",
        "tenant_id": "system",
        "roles": ["system_admin"],
        "iat": 1234567890,
        "exp": 1234571490,
        "aud": "auth-service",
    }

    print("System Admin JWT Claims:")
    print(json.dumps(system_jwt_claims, indent=2))

    system_user = create_user_from_jwt_claims(system_jwt_claims)

    if system_user:
        print(f"\nConverted System User:")
        print(f"  User ID: {system_user.user_id}")
        print(f"  Tenant ID: {system_user.tenant_id}")
        print(f"  Roles: {[role.value for role in system_user.roles]}")
        print(f"  Permission count: {len(system_user.permissions)}")
        print(
            f"  Has system admin permission: {system_user.has_permission(Permission.SYSTEM_ADMIN)}"
        )


def demo_role_permissions():
    """Demonstrate role-to-permissions mapping."""
    print("=== Role Permissions Demo ===\n")

    from app.rbac.models import ROLE_PERMISSIONS

    for role in Role:
        permissions = ROLE_PERMISSIONS.get(role, [])
        print(f"{role.value}:")
        print(f"  Permissions ({len(permissions)}):")
        for perm in permissions:
            print(f"    - {perm.value}")
        print()


def main():
    """Run all demos."""
    print("RBAC (Role-Based Access Control) Demo")
    print("=" * 60)
    print()

    demo_rbac_models()
    demo_jwt_claims()
    demo_role_permissions()

    print("Demo completed!")


if __name__ == "__main__":
    main()
