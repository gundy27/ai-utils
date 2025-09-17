from __future__ import annotations

import base64
import os
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_PRIVATE_KEY = None
_PUBLIC_KEY_PEM: bytes | None = None
_KID: str | None = None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _compute_kid(public_pem: bytes) -> str:
    # Simple KID: hash-like using b64 of first bytes; for prod use a stable KID scheme
    return _b64url(public_pem[:16])


def _ensure_keys() -> None:
    global _PRIVATE_KEY, _PUBLIC_KEY_PEM, _KID
    if _PRIVATE_KEY is not None:
        return
    # Generate RSA keypair for dev; in prod load from KMS/HSM or env
    key_size = int(os.environ.get("JWT_RSA_KEY_SIZE", "2048"))
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    _PRIVATE_KEY = private_key
    _PUBLIC_KEY_PEM = public_pem
    _KID = _compute_kid(public_pem)


def get_private_key():
    _ensure_keys()
    return _PRIVATE_KEY


def get_public_pem() -> bytes:
    _ensure_keys()
    assert _PUBLIC_KEY_PEM is not None
    return _PUBLIC_KEY_PEM


def get_kid() -> str:
    _ensure_keys()
    assert _KID is not None
    return _KID


def get_jwks() -> dict[str, Any]:
    # Build minimal RS256 JWKS from public key
    from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod

    pub = serialization.load_pem_public_key(get_public_pem())
    assert isinstance(pub, rsa_mod.RSAPublicKey)
    numbers = pub.public_numbers()
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": get_kid(),
        "alg": "RS256",
        "n": _b64url(n),
        "e": _b64url(e),
    }
    return {"keys": [jwk]}
