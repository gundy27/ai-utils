from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .models import AuditEvent, AuditEventType, AuditResult, create_audit_event
from .storage import audit_storage

logger = structlog.get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware for automatic audit logging of HTTP requests."""

    def __init__(self, app, exclude_paths: Optional[list[str]] = None):
        """
        Initialize audit middleware.

        Args:
            app: FastAPI application
            exclude_paths: List of paths to exclude from audit logging
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]
        self.logger = logger.bind(component="audit_middleware")

        self.logger.info(
            "audit_middleware_initialized", exclude_paths=self.exclude_paths
        )

    async def dispatch(self, request: Request, call_next):
        """Process request and log audit events."""
        start_time = time.time()

        # Generate request ID for tracking
        request_id = str(uuid.uuid4())

        # Extract request information
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")

        # Skip audit for excluded paths
        if self._should_skip_audit(path):
            return await call_next(request)

        # Try to extract user information from request
        actor_id, tenant_id = self._extract_user_info(request)

        # Log request start
        self.logger.debug(
            "audit_request_start",
            request_id=request_id,
            method=method,
            path=path,
            actor_id=actor_id,
            tenant_id=tenant_id,
            client_ip=client_ip,
        )

        try:
            # Process the request
            response = await call_next(request)

            # Calculate processing time
            duration = time.time() - start_time

            # Log successful request
            await self._log_request_event(
                request_id=request_id,
                method=method,
                path=path,
                actor_id=actor_id,
                tenant_id=tenant_id,
                client_ip=client_ip,
                user_agent=user_agent,
                status_code=response.status_code,
                duration=duration,
                result=(
                    AuditResult.SUCCESS
                    if response.status_code < 400
                    else AuditResult.FAILURE
                ),
                metadata={
                    "request_id": request_id,
                    "duration_ms": round(duration * 1000, 2),
                    "response_size": (
                        getattr(response, "body", b"").__len__()
                        if hasattr(response, "body")
                        else 0
                    ),
                },
            )

            return response

        except Exception as e:
            # Calculate processing time
            duration = time.time() - start_time

            # Log failed request
            await self._log_request_event(
                request_id=request_id,
                method=method,
                path=path,
                actor_id=actor_id,
                tenant_id=tenant_id,
                client_ip=client_ip,
                user_agent=user_agent,
                status_code=500,
                duration=duration,
                result=AuditResult.ERROR,
                metadata={
                    "request_id": request_id,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )

            raise

    def _should_skip_audit(self, path: str) -> bool:
        """Check if path should be excluded from audit logging."""
        return any(path.startswith(exclude_path) for exclude_path in self.exclude_paths)

    def _get_client_ip(self, request: Request) -> Optional[str]:
        """Extract client IP address from request."""
        # Check for forwarded headers first (for load balancers/proxies)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host

        return None

    def _extract_user_info(
        self, request: Request
    ) -> tuple[Optional[str], Optional[str]]:
        """Extract user ID and tenant ID from request."""
        try:
            # Try to get user info from JWT token in Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]

                # Validate JWT and extract claims
                from ..auth.jwt_service import validate_jwt

                validation_result = validate_jwt(token)

                if validation_result and validation_result.get("active"):
                    claims = validation_result.get("claims", {})
                    user_id = claims.get("sub")
                    tenant_id = claims.get("tenant_id")
                    return user_id, tenant_id
        except Exception:
            # If JWT validation fails, continue without user info
            pass

        return None, None

    async def _log_request_event(
        self,
        request_id: str,
        method: str,
        path: str,
        actor_id: Optional[str],
        tenant_id: Optional[str],
        client_ip: Optional[str],
        user_agent: Optional[str],
        status_code: int,
        duration: float,
        result: AuditResult,
        metadata: Dict[str, Any],
    ) -> None:
        """Log an audit event for the request."""
        try:
            # Determine event type based on path and method
            event_type = self._determine_event_type(method, path, status_code)

            # Use system actor if no user identified
            if not actor_id:
                actor_id = "system"
                actor_type = "system"
            else:
                actor_type = "user"

            # Use default tenant if no tenant identified
            if not tenant_id:
                tenant_id = "system"

            # Create audit event
            event = create_audit_event(
                event_type=event_type,
                result=result,
                actor_id=actor_id,
                tenant_id=tenant_id,
                action=f"{method} {path}",
                description=f"HTTP {method} request to {path}",
                actor_type=actor_type,
                actor_ip=client_ip,
                actor_user_agent=user_agent,
                request_id=request_id,
                method=method,
                path=path,
                status_code=status_code,
                metadata=metadata,
                tags=["http_request", "api_call"],
            )

            # Store the event
            audit_storage.store_event(event)

            self.logger.debug(
                "audit_event_logged",
                event_id=event.event_id,
                event_type=event_type,
                actor_id=actor_id,
                tenant_id=tenant_id,
                result=result,
                request_id=request_id,
            )

        except Exception as e:
            # Don't let audit logging errors break the request
            self.logger.error(
                "audit_logging_error",
                error=str(e),
                request_id=request_id,
                method=method,
                path=path,
            )

    def _determine_event_type(
        self, method: str, path: str, status_code: int
    ) -> AuditEventType:
        """Determine audit event type based on request details."""
        # Authentication endpoints
        if path.startswith("/auth/"):
            if "jwt/issue" in path:
                return AuditEventType.AUTH_TOKEN_ISSUED
            elif "jwt/validate" in path:
                return AuditEventType.AUTH_TOKEN_VALIDATED
            elif "oauth/token" in path:
                return AuditEventType.AUTH_TOKEN_ISSUED
            else:
                return AuditEventType.AUTH_LOGIN

        # Secret endpoints
        elif path.startswith("/secrets/"):
            if "fetch" in path:
                return AuditEventType.SECRET_FETCH
            elif "rotate" in path:
                return AuditEventType.SECRET_ROTATE
            elif "delete" in path:
                return AuditEventType.SECRET_DELETE
            else:
                return AuditEventType.SECRET_FETCH  # Default for secrets

        # Audit endpoints
        elif path.startswith("/audit/"):
            return AuditEventType.ACCESS_GRANTED  # Reading audit logs

        # Default based on status code
        elif status_code >= 400:
            return AuditEventType.ACCESS_DENIED
        else:
            return AuditEventType.ACCESS_GRANTED


def log_custom_event(
    event_type: AuditEventType,
    result: AuditResult,
    actor_id: str,
    tenant_id: str,
    action: str,
    description: str,
    **kwargs: Any,
) -> None:
    """
    Log a custom audit event.

    Args:
        event_type: Type of audit event
        result: Result of the event
        actor_id: ID of the actor performing the action
        tenant_id: Tenant ID
        action: Action being performed
        description: Description of the event
        **kwargs: Additional event parameters
    """
    try:
        event = create_audit_event(
            event_type=event_type,
            result=result,
            actor_id=actor_id,
            tenant_id=tenant_id,
            action=action,
            description=description,
            **kwargs,
        )

        audit_storage.store_event(event)

        logger.debug(
            "custom_audit_event_logged",
            event_id=event.event_id,
            event_type=event_type,
            actor_id=actor_id,
            tenant_id=tenant_id,
            result=result,
        )

    except Exception as e:
        logger.error(
            "custom_audit_logging_error",
            error=str(e),
            event_type=event_type,
            actor_id=actor_id,
            tenant_id=tenant_id,
        )
