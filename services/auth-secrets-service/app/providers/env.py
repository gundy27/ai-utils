from __future__ import annotations

import os

from .base import SecretRef, SecretsProvider


class EnvSecretsProvider(SecretsProvider):
    """Reads secrets from environment variables.

    Convention: ENV_SECRET__{SCOPE}__{NAME}__{VERSION}
    If VERSION is missing, looks for ENV_SECRET__{SCOPE}__{NAME}
    SCOPE/NAME should avoid spaces; use / for path-like scopes.
    """

    def _keys(self, ref: SecretRef) -> list[str]:
        base = f"ENV_SECRET__{ref.scope}__{ref.name}"
        if ref.version:
            return [f"{base}__{ref.version}", base]
        return [base]

    def get_secret(self, ref: SecretRef) -> tuple[str, dict[str, str]]:
        for k in self._keys(ref):
            v = os.environ.get(k)
            if v is not None:
                meta = {"provider": "env", "key": k}
                return v, meta
        raise KeyError("secret_not_found")

    def rotate_secret(
        self, ref: SecretRef, reason: str | None = None, dry_run: bool = False
    ) -> dict[str, str]:
        # Not supported for env provider; return stub metadata
        return {"status": "unsupported", "provider": "env"}
