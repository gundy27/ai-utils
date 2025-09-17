from __future__ import annotations

import os
from typing import Any, Dict, Optional

import hvac
import structlog

from .base import SecretRef, SecretsProvider

logger = structlog.get_logger(__name__)


class VaultSecretsProvider(SecretsProvider):
    """HashiCorp Vault provider for secrets management.

    Supports multiple authentication methods:
    - Token-based authentication
    - AppRole authentication
    - Kubernetes authentication
    - AWS IAM authentication

    Name resolution strategy:
    - Secret path is constructed as: {mount_point}/data/{tenant_id}/{scope}/{name}
    - Supports KV v2 secrets engine by default
    - Version can be specified via ref.version for KV v2
    """

    def __init__(self) -> None:
        """Initialize Vault client with authentication."""
        self.logger = logger.bind(component="vault_provider")

        # Vault connection settings
        vault_url = os.environ.get("VAULT_ADDR", "http://localhost:8200")
        verify_ssl = os.environ.get("VAULT_SKIP_VERIFY", "false").lower() == "false"

        # Initialize Vault client
        self.client = hvac.Client(url=vault_url, verify=verify_ssl)

        # Mount point for KV secrets engine
        self.mount_point = os.environ.get("VAULT_MOUNT_POINT", "secret")

        # Authenticate with Vault
        self._authenticate()

        self.logger.info(
            "vault_provider_initialized",
            vault_url=vault_url,
            mount_point=self.mount_point,
            verify_ssl=verify_ssl,
        )

    def _authenticate(self) -> None:
        """Authenticate with Vault using the configured method."""
        auth_method = os.environ.get("VAULT_AUTH_METHOD", "token").lower()

        try:
            if auth_method == "token":
                self._authenticate_with_token()
            elif auth_method == "approle":
                self._authenticate_with_approle()
            elif auth_method == "kubernetes":
                self._authenticate_with_kubernetes()
            elif auth_method == "aws":
                self._authenticate_with_aws()
            else:
                raise ValueError(f"Unsupported Vault auth method: {auth_method}")

            # Verify authentication
            if not self.client.is_authenticated():
                raise RuntimeError("Failed to authenticate with Vault")

            self.logger.info("vault_authentication_successful", auth_method=auth_method)

        except Exception as e:
            self.logger.error(
                "vault_authentication_failed", auth_method=auth_method, error=str(e)
            )
            raise

    def _authenticate_with_token(self) -> None:
        """Authenticate using Vault token."""
        token = os.environ.get("VAULT_TOKEN")
        if not token:
            raise ValueError(
                "VAULT_TOKEN environment variable is required for token authentication"
            )

        self.client.token = token

    def _authenticate_with_approle(self) -> None:
        """Authenticate using AppRole method."""
        role_id = os.environ.get("VAULT_ROLE_ID")
        secret_id = os.environ.get("VAULT_SECRET_ID")
        mount_point = os.environ.get("VAULT_APPROLE_MOUNT", "approle")

        if not role_id or not secret_id:
            raise ValueError(
                "VAULT_ROLE_ID and VAULT_SECRET_ID are required for AppRole authentication"
            )

        response = self.client.auth.approle.login(
            role_id=role_id,
            secret_id=secret_id,
            mount_point=mount_point,
        )

        if "auth" in response and "client_token" in response["auth"]:
            self.client.token = response["auth"]["client_token"]
        else:
            raise RuntimeError("Invalid response from Vault AppRole authentication")

    def _authenticate_with_kubernetes(self) -> None:
        """Authenticate using Kubernetes method."""
        role = os.environ.get("VAULT_K8S_ROLE")
        mount_point = os.environ.get("VAULT_K8S_MOUNT", "kubernetes")
        token_path = os.environ.get(
            "VAULT_K8S_TOKEN_PATH",
            "/var/run/secrets/kubernetes.io/serviceaccount/token",
        )

        if not role:
            raise ValueError("VAULT_K8S_ROLE is required for Kubernetes authentication")

        # Read Kubernetes service account token
        try:
            with open(token_path, "r") as f:
                jwt_token = f.read().strip()
        except FileNotFoundError:
            raise ValueError(f"Kubernetes token file not found at {token_path}")

        response = self.client.auth.kubernetes.login(
            role=role,
            jwt=jwt_token,
            mount_point=mount_point,
        )

        if "auth" in response and "client_token" in response["auth"]:
            self.client.token = response["auth"]["client_token"]
        else:
            raise RuntimeError("Invalid response from Vault Kubernetes authentication")

    def _authenticate_with_aws(self) -> None:
        """Authenticate using AWS IAM method."""
        role = os.environ.get("VAULT_AWS_ROLE")
        mount_point = os.environ.get("VAULT_AWS_MOUNT", "aws")
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

        if not role:
            raise ValueError("VAULT_AWS_ROLE is required for AWS authentication")

        if not aws_access_key or not aws_secret_key:
            raise ValueError(
                "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required for AWS authentication"
            )

        # Get AWS credentials and sign the request
        import boto3

        session = boto3.Session(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region,
        )

        credentials = session.get_credentials()

        response = self.client.auth.aws.iam_login(
            access_key=credentials.access_key,
            secret_key=credentials.secret_key,
            session_token=credentials.token,
            role=role,
            mount_point=mount_point,
        )

        if "auth" in response and "client_token" in response["auth"]:
            self.client.token = response["auth"]["client_token"]
        else:
            raise RuntimeError("Invalid response from Vault AWS authentication")

    def _secret_path(self, ref: SecretRef) -> str:
        """Construct the Vault secret path."""
        # For KV v2, the path structure is: mount_point/data/tenant_id/scope/name
        parts = [ref.tenant_id, ref.scope, ref.name]
        path = "/".join([p.strip("/") for p in parts if p])
        return f"{self.mount_point}/data/{path}"

    def get_secret(self, ref: SecretRef) -> tuple[str, dict[str, str]]:
        """Retrieve a secret from Vault."""
        secret_path = self._secret_path(ref)

        try:
            # For KV v2, use read_secret_version
            if ref.version:
                # Version can be a version number or 'latest'
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=secret_path.replace(f"{self.mount_point}/data/", ""),
                    mount_point=self.mount_point,
                    version=int(ref.version) if ref.version.isdigit() else None,
                )
            else:
                # Get latest version
                response = self.client.secrets.kv.v2.read_secret_version(
                    path=secret_path.replace(f"{self.mount_point}/data/", ""),
                    mount_point=self.mount_point,
                )

            if not response or "data" not in response:
                raise KeyError(f"Secret not found at path: {secret_path}")

            secret_data = response["data"]["data"]

            # Extract the secret value - assume single key-value pair or use 'value' key
            if len(secret_data) == 1:
                value = list(secret_data.values())[0]
            elif "value" in secret_data:
                value = secret_data["value"]
            else:
                # Return JSON string if multiple values
                import json

                value = json.dumps(secret_data)

            metadata = {
                "provider": "vault",
                "path": secret_path,
                "version": str(response["data"]["metadata"]["version"]),
                "created_time": response["data"]["metadata"]["created_time"],
                "deletion_time": response["data"]["metadata"].get("deletion_time", ""),
                "destroyed": str(response["data"]["metadata"].get("destroyed", False)),
                "mount_point": self.mount_point,
            }

            self.logger.debug(
                "vault_secret_retrieved",
                path=secret_path,
                version=metadata["version"],
                has_value=bool(value),
            )

            return str(value), metadata

        except hvac.exceptions.InvalidPath:
            self.logger.warning("vault_secret_not_found", path=secret_path)
            raise KeyError(f"Secret not found at path: {secret_path}")
        except Exception as e:
            self.logger.error(
                "vault_secret_retrieval_error", path=secret_path, error=str(e)
            )
            raise

    def rotate_secret(
        self, ref: SecretRef, reason: str | None = None, dry_run: bool = False
    ) -> dict[str, str]:
        """Rotate a secret in Vault."""
        if dry_run:
            return {
                "status": "dry_run",
                "provider": "vault",
                "message": "Dry run - no rotation performed",
            }

        secret_path = self._secret_path(ref)

        try:
            # Get current secret to preserve its value structure
            current_value, current_meta = self.get_secret(ref)

            # For rotation, we could:
            # 1. Generate a new secret value
            # 2. Update the secret in Vault
            # 3. Return rotation metadata

            # For now, we'll implement a simple version increment approach
            # In production, you'd want to integrate with actual secret generation logic

            import json
            import time

            # Parse current secret if it's JSON
            try:
                secret_data = json.loads(current_value)
            except (json.JSONDecodeError, TypeError):
                # If not JSON, treat as simple value
                secret_data = {"value": current_value}

            # Add rotation metadata
            secret_data["_rotation"] = {
                "rotated_at": time.time(),
                "rotated_by": "auth-secrets-service",
                "reason": reason or "manual_rotation",
                "previous_version": current_meta.get("version"),
            }

            # Write new version to Vault
            path_without_mount = secret_path.replace(f"{self.mount_point}/data/", "")
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path_without_mount,
                secret=secret_data,
                mount_point=self.mount_point,
            )

            # Get the new version
            new_value, new_meta = self.get_secret(ref)

            result = {
                "status": "success",
                "provider": "vault",
                "previous_version": current_meta.get("version"),
                "new_version": new_meta.get("version"),
                "path": secret_path,
                "rotated_at": secret_data["_rotation"]["rotated_at"],
            }

            self.logger.info(
                "vault_secret_rotated",
                path=secret_path,
                previous_version=result["previous_version"],
                new_version=result["new_version"],
            )

            return result

        except Exception as e:
            self.logger.error(
                "vault_secret_rotation_error", path=secret_path, error=str(e)
            )
            return {
                "status": "error",
                "provider": "vault",
                "error": str(e),
                "path": secret_path,
            }

    def list_secrets(self, tenant_id: str, scope: str = "") -> list[str]:
        """List secrets for a tenant/scope."""
        try:
            # Construct the path for listing
            path_parts = [tenant_id]
            if scope:
                path_parts.append(scope)

            path = "/".join(path_parts)

            # List secrets at the path
            response = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self.mount_point,
            )

            if "data" in response and "keys" in response["data"]:
                return response["data"]["keys"]
            else:
                return []

        except hvac.exceptions.InvalidPath:
            # Path doesn't exist, return empty list
            return []
        except Exception as e:
            self.logger.error(
                "vault_list_secrets_error",
                tenant_id=tenant_id,
                scope=scope,
                error=str(e),
            )
            return []

    def delete_secret(self, ref: SecretRef) -> dict[str, str]:
        """Delete a secret from Vault."""
        secret_path = self._secret_path(ref)

        try:
            path_without_mount = secret_path.replace(f"{self.mount_point}/data/", "")

            # Soft delete (mark for deletion)
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=path_without_mount,
                mount_point=self.mount_point,
            )

            result = {
                "status": "success",
                "provider": "vault",
                "path": secret_path,
                "deleted": True,
            }

            self.logger.info("vault_secret_deleted", path=secret_path)
            return result

        except Exception as e:
            self.logger.error(
                "vault_secret_deletion_error", path=secret_path, error=str(e)
            )
            return {
                "status": "error",
                "provider": "vault",
                "error": str(e),
                "path": secret_path,
            }
