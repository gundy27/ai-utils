"""RBAC (Role-Based Access Control) module for auth-secrets-service."""

from .models import (
    Permission,
    Role,
    User,
    create_user_from_jwt_claims,
    get_permissions_for_role,
)
from .middleware import RBACError, RBACMiddleware, get_current_user, rbac_middleware

__all__ = [
    "Permission",
    "Role",
    "User",
    "RBACError",
    "RBACMiddleware",
    "rbac_middleware",
    "get_current_user",
    "create_user_from_jwt_claims",
    "get_permissions_for_role",
]
