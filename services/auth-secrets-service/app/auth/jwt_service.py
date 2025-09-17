from __future__ import annotations

import os
import time
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization

from .keys import get_kid, get_private_key, get_public_pem
from ..rbac.models import Role


def issue_jwt(
    subject: str,
    tenant_id: str,
    scopes: list[str],
    audience: str,
    ttl_s: int,
    roles: list[Role] | None = None,
) -> dict[str, Any]:
    now = int(time.time())

    # Include RBAC information in JWT claims
    payload = {
        "sub": subject,
        "tenant_id": tenant_id,  # Standardized field name
        "scope": " ".join(scopes),
        "iss": os.environ.get("JWT_ISSUER", "https://auth.local"),
        "aud": audience,
        "iat": now,
        "exp": now + ttl_s,
    }

    # Add roles if provided
    if roles:
        payload["roles"] = [role.value for role in roles]

    private_key = get_private_key()
    pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    token = jwt.encode(payload, pem, algorithm="RS256", headers={"kid": get_kid()})
    return {"access_token": token, "token_type": "bearer", "expires_in": ttl_s}


def validate_jwt(token: str, audience: str | None = None) -> dict[str, Any]:
    options = {"verify_aud": audience is not None}
    claims = jwt.decode(
        token,
        get_public_pem(),
        algorithms=["RS256"],
        audience=audience,
        issuer=os.environ.get("JWT_ISSUER", "https://auth.local"),
        options=options,
    )
    return {"active": True, "claims": claims}
