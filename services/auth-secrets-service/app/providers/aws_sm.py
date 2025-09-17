from __future__ import annotations

import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from .base import SecretRef, SecretsProvider


class AwsSecretsManagerProvider(SecretsProvider):
    """AWS Secrets Manager provider.

    Name resolution strategy (simple):
    - SecretId is constructed as: {tenant_id}/{scope}/{name}
      e.g., acme/prod/app/API_KEY
    - VersionStage or VersionId can be used if provided via ref.version
      (we treat version as VersionStage first; if not found, we try VersionId)
    """

    def __init__(self) -> None:
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        self._client = boto3.client("secretsmanager", region_name=region)

    def _secret_id(self, ref: SecretRef) -> str:
        parts = [ref.tenant_id, ref.scope, ref.name]
        return "/".join([p.strip("/") for p in parts if p])

    def get_secret(self, ref: SecretRef) -> tuple[str, dict[str, str]]:
        secret_id = self._secret_id(ref)
        kwargs: dict[str, Any] = {"SecretId": secret_id}
        if ref.version:
            # Try as VersionStage first, then VersionId
            try:
                resp = self._client.get_secret_value(**kwargs, VersionStage=ref.version)
            except ClientError:
                resp = self._client.get_secret_value(**kwargs, VersionId=ref.version)
        else:
            resp = self._client.get_secret_value(**kwargs)

        if "SecretString" in resp:
            value = resp["SecretString"]
        else:
            # binary
            value = resp["SecretBinary"].decode("utf-8")

        meta = {
            "provider": "aws_secrets_manager",
            "secret_id": secret_id,
            "version_id": resp.get("VersionId", ""),
        }
        return value, meta

    def rotate_secret(
        self, ref: SecretRef, reason: str | None = None, dry_run: bool = False
    ) -> dict[str, str]:
        # Minimal placeholder: production rotation typically uses rotation lambdas
        # Here we signal unsupported to avoid implying rotation occurred
        return {"status": "unsupported", "provider": "aws_secrets_manager"}
