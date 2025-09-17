from __future__ import annotations

import structlog
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import Permission, User, create_user_from_jwt_claims

logger = structlog.get_logger(__name__)
security = HTTPBearer(auto_error=False)


class RBACError(HTTPException):
    """Custom exception for RBAC-related errors."""

    def __init__(self, status_code: int, detail: str, error_code: str = "rbac_error"):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code


class RBACMiddleware:
    """RBAC middleware for request authorization."""

    def __init__(self):
        self.logger = logger.bind(component="rbac")

    async def validate_request(
        self,
        request: Request,
        required_permission: Permission,
        target_tenant_id: str | None = None,
    ) -> User:
        """
        Validate that the request has the required permission.

        Args:
            request: FastAPI request object
            required_permission: Permission required for this request
            target_tenant_id: Tenant ID being accessed (for tenant isolation)

        Returns:
            User object if authorized

        Raises:
            RBACError: If authorization fails
        """
        # Extract and validate JWT token
        user = await self._extract_user_from_request(request)

        # Check tenant access
        if target_tenant_id and not user.can_access_tenant(target_tenant_id):
            self.logger.warning(
                "tenant_access_denied",
                user_id=user.user_id,
                user_tenant=user.tenant_id,
                target_tenant=target_tenant_id,
            )
            raise RBACError(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to tenant {target_tenant_id}",
                error_code="tenant_access_denied",
            )

        # Check permission
        effective_tenant = target_tenant_id or user.tenant_id
        effective_permissions = user.get_effective_permissions(effective_tenant)

        if required_permission not in effective_permissions:
            self.logger.warning(
                "permission_denied",
                user_id=user.user_id,
                tenant_id=effective_tenant,
                required_permission=required_permission,
                user_permissions=effective_permissions,
            )
            raise RBACError(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission {required_permission} required",
                error_code="permission_denied",
            )

        self.logger.info(
            "request_authorized",
            user_id=user.user_id,
            tenant_id=effective_tenant,
            permission=required_permission,
        )

        return user

    async def _extract_user_from_request(self, request: Request) -> User:
        """Extract and validate user from request JWT token."""
        # Get Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise RBACError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header",
                error_code="missing_token",
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            # Validate JWT and extract claims
            from ..auth.jwt_service import validate_jwt

            validation_result = validate_jwt(token)
            if not validation_result:
                raise RBACError(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    error_code="invalid_token",
                )

            claims = validation_result.get("claims", {})
            user = create_user_from_jwt_claims(claims)

            if not user:
                raise RBACError(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid user claims in token",
                    error_code="invalid_user_claims",
                )

            if not user.is_active:
                raise RBACError(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account is inactive",
                    error_code="user_inactive",
                )

            return user

        except Exception as e:
            if isinstance(e, RBACError):
                raise
            self.logger.error("token_validation_error", error=str(e))
            raise RBACError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token validation failed",
                error_code="token_validation_error",
            )


# Global RBAC middleware instance
rbac_middleware = RBACMiddleware()


def require_permission(permission: Permission, tenant_param: str = "tenant_id"):
    """
    Decorator to require a specific permission for an endpoint.

    Args:
        permission: Required permission
        tenant_param: Name of the parameter containing tenant_id
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This would be used in FastAPI dependency injection
            # For now, we'll implement this in the routers directly
            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def get_current_user(request: Request) -> User:
    """FastAPI dependency to get current authenticated user."""
    return await rbac_middleware._extract_user_from_request(request)


async def require_permission_dependency(
    request: Request,
    permission: Permission,
    tenant_id: str | None = None,
) -> User:
    """FastAPI dependency for permission-based authorization."""
    return await rbac_middleware.validate_request(request, permission, tenant_id)
