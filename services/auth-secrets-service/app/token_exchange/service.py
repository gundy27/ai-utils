"""Token exchange service layer for handling delegation and impersonation."""

from __future__ import annotations

import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any, List

import structlog

from .models import (
    TokenExchangeRequest,
    TokenExchangeResponse,
    TokenExchangeError,
    DelegationRequest,
    DelegationResponse,
    ImpersonationRequest,
    ImpersonationResponse,
    DelegationPolicy,
    TokenExchangeAuditEvent,
    TokenExchangeErrorType,
    create_token_exchange_error,
    validate_delegation_chain,
    build_delegation_audit_event,
)
from .storage import token_exchange_storage
from ..auth.jwt_service import validate_jwt, issue_jwt
from ..rbac.models import Role

logger = structlog.get_logger(__name__)


class TokenExchangeService:
    """Token exchange service for handling delegation and impersonation."""

    def __init__(self):
        """Initialize the token exchange service."""
        self.logger = logger.bind(component="token_exchange_service")
        self.storage = token_exchange_storage

        # Configuration
        self.default_access_token_ttl = 3600  # 1 hour
        self.max_delegation_depth = 5
        self.impersonation_token_ttl = 1800  # 30 minutes

        self.logger.info("token_exchange_service_initialized")

    def validate_token_exchange_request(
        self, request: TokenExchangeRequest, client_id: str
    ) -> Tuple[bool, Optional[TokenExchangeError]]:
        """Validate a token exchange request."""
        try:
            # Validate subject token
            try:
                subject_claims = self._validate_and_parse_token(request.subject_token)
                if not subject_claims:
                    return False, create_token_exchange_error(
                        TokenExchangeErrorType.INVALID_GRANT, "Invalid subject token"
                    )
            except Exception as e:
                return False, create_token_exchange_error(
                    TokenExchangeErrorType.INVALID_GRANT,
                    f"Subject token validation failed: {str(e)}",
                )

            # Validate actor token if provided
            if request.actor_token:
                try:
                    actor_claims = self._validate_and_parse_token(request.actor_token)
                    if not actor_claims:
                        return False, create_token_exchange_error(
                            TokenExchangeErrorType.INVALID_GRANT, "Invalid actor token"
                        )
                except Exception as e:
                    return False, create_token_exchange_error(
                        TokenExchangeErrorType.INVALID_GRANT,
                        f"Actor token validation failed: {str(e)}",
                    )

            # Parse requested scopes
            requested_scopes = []
            if request.scope:
                requested_scopes = request.scope.split()

            # Find matching delegation policy
            policy = self.storage.find_matching_policy(
                source_scopes=subject_claims.get("scope", "").split(),
                target_scopes=requested_scopes,
                audience=request.audience,
                tenant_id=subject_claims.get("tenant_id"),
            )

            if not policy:
                return False, create_token_exchange_error(
                    TokenExchangeErrorType.INVALID_SCOPE,
                    "No delegation policy found for requested scopes",
                )

            return True, None

        except Exception as e:
            self.logger.error("token_exchange_validation_error", error=str(e))
            return False, create_token_exchange_error(
                TokenExchangeErrorType.SERVER_ERROR, "Internal server error"
            )

    def exchange_token(
        self, request: TokenExchangeRequest, client_id: str
    ) -> TokenExchangeResponse:
        """Exchange a token for a new token with different scopes/audience."""
        try:
            # Validate the request
            is_valid, error = self.validate_token_exchange_request(request, client_id)
            if not is_valid:
                raise ValueError(
                    error.error_description or "Token exchange validation failed"
                )

            # Parse subject token
            subject_claims = self._validate_and_parse_token(request.subject_token)

            # Parse requested scopes
            requested_scopes = []
            if request.scope:
                requested_scopes = request.scope.split()

            # Find delegation policy
            policy = self.storage.find_matching_policy(
                source_scopes=subject_claims.get("scope", "").split(),
                target_scopes=requested_scopes,
                audience=request.audience,
                tenant_id=subject_claims.get("tenant_id"),
            )

            # Generate new token
            expires_in = policy.expires_in_override or self.default_access_token_ttl

            # Extract roles if present
            roles = []
            if "roles" in subject_claims:
                roles = [
                    Role(role) for role in subject_claims["roles"] if Role(role) in Role
                ]

            new_token_response = issue_jwt(
                subject=subject_claims.get("sub", "unknown"),
                tenant_id=subject_claims.get("tenant_id", "unknown"),
                scopes=requested_scopes,
                audience=request.audience or "default",
                ttl_s=expires_in,
                roles=roles,
            )

            # Create audit event
            audit_event = build_delegation_audit_event(
                event_type="token_exchange",
                actor_id=subject_claims.get("sub", "unknown"),
                tenant_id=subject_claims.get("tenant_id", "unknown"),
                source_token=request.subject_token[:8] + "...",
                target_token=new_token_response["access_token"][:8] + "...",
                source_scopes=subject_claims.get("scope", "").split(),
                target_scopes=requested_scopes,
                success=True,
                audience=request.audience,
                metadata={"client_id": client_id},
            )

            self.storage.store_audit_event(audit_event)

            self.logger.info(
                "token_exchange_successful",
                actor_id=subject_claims.get("sub"),
                tenant_id=subject_claims.get("tenant_id"),
                source_scopes=subject_claims.get("scope", "").split(),
                target_scopes=requested_scopes,
                audience=request.audience,
            )

            return TokenExchangeResponse(
                access_token=new_token_response["access_token"],
                issued_token_type=request.requested_token_type.value,
                token_type="Bearer",
                expires_in=expires_in,
                scope=" ".join(requested_scopes) if requested_scopes else None,
            )

        except Exception as e:
            self.logger.error("token_exchange_error", error=str(e))

            # Create failure audit event
            audit_event = build_delegation_audit_event(
                event_type="token_exchange_failed",
                actor_id="unknown",
                tenant_id="unknown",
                source_token=request.subject_token[:8] + "...",
                target_token="",
                source_scopes=[],
                target_scopes=[],
                success=False,
                error_message=str(e),
                metadata={"client_id": client_id},
            )

            self.storage.store_audit_event(audit_event)
            raise

    def delegate_token(
        self, request: DelegationRequest, client_id: str
    ) -> DelegationResponse:
        """Delegate a token to another service."""
        try:
            # Validate source token
            source_claims = self._validate_and_parse_token(request.source_token)

            # Check delegation chain
            if not validate_delegation_chain(
                request.delegation_chain, self.max_delegation_depth
            ):
                raise ValueError("Delegation chain too long or contains cycles")

            # Find delegation policy
            policy = self.storage.find_matching_policy(
                source_scopes=source_claims.get("scope", "").split(),
                target_scopes=request.target_scopes,
                audience=request.target_audience,
                tenant_id=source_claims.get("tenant_id"),
            )

            if not policy:
                raise ValueError("No delegation policy found")

            # Check delegation depth
            if len(request.delegation_chain) >= policy.max_delegation_depth:
                raise ValueError("Maximum delegation depth exceeded")

            # Generate delegated token
            expires_in = request.expires_in
            if policy.expires_in_override:
                expires_in = min(expires_in, policy.expires_in_override)

            # Extract roles if present
            roles = []
            if "roles" in source_claims:
                roles = [
                    Role(role) for role in source_claims["roles"] if Role(role) in Role
                ]

            delegated_token_response = issue_jwt(
                subject=source_claims.get("sub", "unknown"),
                tenant_id=source_claims.get("tenant_id", "unknown"),
                scopes=request.target_scopes,
                audience=request.target_audience,
                ttl_s=expires_in,
                roles=roles,
            )

            # Update delegation chain
            new_delegation_chain = request.delegation_chain + [
                request.source_token[:8] + "..."
            ]

            # Create audit event
            audit_event = build_delegation_audit_event(
                event_type="token_delegation",
                actor_id=source_claims.get("sub", "unknown"),
                tenant_id=source_claims.get("tenant_id", "unknown"),
                source_token=request.source_token[:8] + "...",
                target_token=delegated_token_response["access_token"][:8] + "...",
                source_scopes=source_claims.get("scope", "").split(),
                target_scopes=request.target_scopes,
                success=True,
                delegation_chain=new_delegation_chain,
                audience=request.target_audience,
                metadata={
                    "client_id": client_id,
                    "impersonation": request.impersonation,
                },
            )

            self.storage.store_audit_event(audit_event)

            self.logger.info(
                "token_delegation_successful",
                actor_id=source_claims.get("sub"),
                tenant_id=source_claims.get("tenant_id"),
                target_audience=request.target_audience,
                delegation_depth=len(new_delegation_chain),
            )

            return DelegationResponse(
                delegated_token=delegated_token_response["access_token"],
                token_type="Bearer",
                expires_in=expires_in,
                scope=" ".join(request.target_scopes),
                audience=request.target_audience,
                delegation_chain=new_delegation_chain,
            )

        except Exception as e:
            self.logger.error("token_delegation_error", error=str(e))

            # Create failure audit event
            audit_event = build_delegation_audit_event(
                event_type="token_delegation_failed",
                actor_id="unknown",
                tenant_id="unknown",
                source_token=request.source_token[:8] + "...",
                target_token="",
                source_scopes=[],
                target_scopes=[],
                success=False,
                error_message=str(e),
                delegation_chain=request.delegation_chain,
                metadata={"client_id": client_id},
            )

            self.storage.store_audit_event(audit_event)
            raise

    def impersonate_user(
        self, request: ImpersonationRequest, client_id: str
    ) -> ImpersonationResponse:
        """Impersonate another user (admin operation)."""
        try:
            # Validate source token (must have impersonation permissions)
            source_claims = self._validate_and_parse_token(request.source_token)

            # Check impersonation permissions
            user_roles = []
            if "roles" in source_claims:
                user_roles = [
                    Role(role) for role in source_claims["roles"] if Role(role) in Role
                ]

            if (
                Role.SYSTEM_ADMIN not in user_roles
                and Role.TENANT_ADMIN not in user_roles
            ):
                raise ValueError("Insufficient permissions for impersonation")

            # Find delegation policy for impersonation
            policy = self.storage.find_matching_policy(
                source_scopes=source_claims.get("scope", "").split(),
                target_scopes=request.target_scopes,
                tenant_id=source_claims.get("tenant_id"),
            )

            if not policy or not policy.requires_impersonation_permission:
                raise ValueError("No impersonation policy found")

            # Generate impersonation token
            expires_in = min(request.expires_in, self.impersonation_token_ttl)

            impersonation_token_response = issue_jwt(
                subject=request.target_user_id,
                tenant_id=request.target_tenant_id
                or source_claims.get("tenant_id", "unknown"),
                scopes=request.target_scopes,
                audience="impersonation",
                ttl_s=expires_in,
                roles=[],  # Impersonated user gets their own roles
            )

            # Create audit event
            audit_event = build_delegation_audit_event(
                event_type="user_impersonation",
                actor_id=source_claims.get("sub", "unknown"),
                tenant_id=source_claims.get("tenant_id", "unknown"),
                source_token=request.source_token[:8] + "...",
                target_token=impersonation_token_response["access_token"][:8] + "...",
                source_scopes=source_claims.get("scope", "").split(),
                target_scopes=request.target_scopes,
                success=True,
                impersonation=True,
                impersonated_user_id=request.target_user_id,
                audience="impersonation",
                metadata={
                    "client_id": client_id,
                    "impersonation_reason": request.impersonation_reason,
                    "target_tenant_id": request.target_tenant_id,
                },
            )

            self.storage.store_audit_event(audit_event)

            self.logger.warning(  # Use warning level for impersonation
                "user_impersonation_successful",
                actor_id=source_claims.get("sub"),
                tenant_id=source_claims.get("tenant_id"),
                impersonated_user_id=request.target_user_id,
                impersonation_reason=request.impersonation_reason,
            )

            return ImpersonationResponse(
                impersonation_token=impersonation_token_response["access_token"],
                token_type="Bearer",
                expires_in=expires_in,
                scope=" ".join(request.target_scopes),
                impersonated_user_id=request.target_user_id,
                impersonated_tenant_id=request.target_tenant_id
                or source_claims.get("tenant_id", "unknown"),
                impersonation_reason=request.impersonation_reason,
            )

        except Exception as e:
            self.logger.error("user_impersonation_error", error=str(e))

            # Create failure audit event
            audit_event = build_delegation_audit_event(
                event_type="user_impersonation_failed",
                actor_id="unknown",
                tenant_id="unknown",
                source_token=request.source_token[:8] + "...",
                target_token="",
                source_scopes=[],
                target_scopes=[],
                success=False,
                error_message=str(e),
                impersonation=True,
                impersonated_user_id=request.target_user_id,
                metadata={"client_id": client_id},
            )

            self.storage.store_audit_event(audit_event)
            raise

    def _validate_and_parse_token(self, token: str) -> Dict[str, Any]:
        """Validate and parse a JWT token."""
        try:
            # Validate the token
            validation_result = validate_jwt(token)

            if not validation_result.get("active", False):
                raise ValueError("Token is not active")

            claims = validation_result.get("claims", {})

            # Check token expiration
            exp = claims.get("exp", 0)
            if exp and datetime.utcnow().timestamp() > exp:
                raise ValueError("Token has expired")

            return claims

        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid token format")
        except Exception as e:
            raise ValueError(f"Token validation failed: {str(e)}")

    def create_delegation_policy(
        self,
        policy_id: str,
        name: str,
        tenant_id: str,
        source_scopes: List[str] = None,
        target_scopes: List[str] = None,
        allowed_audiences: List[str] = None,
        max_delegation_depth: int = 3,
        requires_impersonation_permission: bool = False,
        expires_in_override: Optional[int] = None,
        conditions: Dict[str, Any] = None,
    ) -> DelegationPolicy:
        """Create a new delegation policy."""
        policy = DelegationPolicy(
            policy_id=policy_id,
            name=name,
            tenant_id=tenant_id,
            source_scopes=source_scopes or [],
            target_scopes=target_scopes or [],
            allowed_audiences=allowed_audiences or [],
            max_delegation_depth=max_delegation_depth,
            requires_impersonation_permission=requires_impersonation_permission,
            expires_in_override=expires_in_override,
            conditions=conditions or {},
        )

        self.storage.store_delegation_policy(policy)

        self.logger.info(
            "delegation_policy_created",
            policy_id=policy_id,
            name=name,
            tenant_id=tenant_id,
        )

        return policy


# Global service instance
token_exchange_service = TokenExchangeService()
