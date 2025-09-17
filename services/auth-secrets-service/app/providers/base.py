from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SecretRef:
    tenant_id: str
    scope: str
    name: str
    version: str | None = None


class SecretsProvider(ABC):
    @abstractmethod
    def get_secret(self, ref: SecretRef) -> tuple[str, dict[str, str]]:
        """Return (value, metadata). Must not log secret values."""

    @abstractmethod
    def rotate_secret(
        self, ref: SecretRef, reason: str | None = None, dry_run: bool = False
    ) -> dict[str, str]:
        """Rotate a secret and return metadata (previous/new version, status)."""
