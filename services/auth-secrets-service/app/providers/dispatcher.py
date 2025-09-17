from __future__ import annotations

import os

from .aws_sm import AwsSecretsManagerProvider
from .base import SecretsProvider
from .env import EnvSecretsProvider
from .vault import VaultSecretsProvider


def get_provider() -> SecretsProvider:
    """Get the configured secrets provider."""
    provider = os.environ.get("SECRETS_PROVIDER", "env").lower()

    if provider == "aws":
        return AwsSecretsManagerProvider()
    elif provider == "vault":
        return VaultSecretsProvider()
    else:
        return EnvSecretsProvider()
