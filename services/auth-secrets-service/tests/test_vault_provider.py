"""Tests for HashiCorp Vault provider."""

import json
import os
import pytest
from unittest.mock import Mock, patch, MagicMock

from app.providers.vault import VaultSecretsProvider
from app.providers.base import SecretRef


class TestVaultSecretsProvider:
    """Test Vault secrets provider functionality."""

    def setup_method(self):
        """Set up test environment variables."""
        # Set up minimal environment for testing
        os.environ["VAULT_ADDR"] = "http://localhost:8200"
        os.environ["VAULT_AUTH_METHOD"] = "token"
        os.environ["VAULT_TOKEN"] = "test-token"
        os.environ["VAULT_MOUNT_POINT"] = "secret"

        # Clear any existing environment variables that might interfere
        for key in list(os.environ.keys()):
            if key.startswith("VAULT_") and key not in [
                "VAULT_ADDR",
                "VAULT_AUTH_METHOD",
                "VAULT_TOKEN",
                "VAULT_MOUNT_POINT",
            ]:
                del os.environ[key]

    def teardown_method(self):
        """Clean up environment variables."""
        # Remove test environment variables
        for key in [
            "VAULT_ADDR",
            "VAULT_AUTH_METHOD",
            "VAULT_TOKEN",
            "VAULT_MOUNT_POINT",
        ]:
            if key in os.environ:
                del os.environ[key]

    @patch("app.providers.vault.hvac.Client")
    def test_vault_provider_initialization(self, mock_hvac_client):
        """Test Vault provider initialization."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()

        assert provider.client == mock_client
        assert provider.mount_point == "secret"
        mock_hvac_client.assert_called_once_with(
            url="http://localhost:8200", verify=True
        )

    @patch("app.providers.vault.hvac.Client")
    def test_vault_provider_with_custom_config(self, mock_hvac_client):
        """Test Vault provider with custom configuration."""
        os.environ["VAULT_ADDR"] = "https://vault.example.com"
        os.environ["VAULT_SKIP_VERIFY"] = "true"
        os.environ["VAULT_MOUNT_POINT"] = "custom-secrets"

        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()

        assert provider.mount_point == "custom-secrets"
        mock_hvac_client.assert_called_once_with(
            url="https://vault.example.com", verify=False
        )

    @patch("app.providers.vault.hvac.Client")
    def test_authenticate_with_token(self, mock_hvac_client):
        """Test token-based authentication."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()

        assert provider.client.token == "test-token"
        mock_client.is_authenticated.assert_called_once()

    @patch("app.providers.vault.hvac.Client")
    def test_authenticate_with_approle(self, mock_hvac_client):
        """Test AppRole authentication."""
        os.environ["VAULT_AUTH_METHOD"] = "approle"
        os.environ["VAULT_ROLE_ID"] = "test-role-id"
        os.environ["VAULT_SECRET_ID"] = "test-secret-id"
        os.environ["VAULT_APPROLE_MOUNT"] = "custom-approle"

        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.auth.approle.login.return_value = {
            "auth": {"client_token": "approle-token"}
        }
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()

        assert provider.client.token == "approle-token"
        mock_client.auth.approle.login.assert_called_once_with(
            role_id="test-role-id",
            secret_id="test-secret-id",
            mount_point="custom-approle",
        )

    @patch("app.providers.vault.hvac.Client")
    @patch("builtins.open", create=True)
    def test_authenticate_with_kubernetes(self, mock_open, mock_hvac_client):
        """Test Kubernetes authentication."""
        os.environ["VAULT_AUTH_METHOD"] = "kubernetes"
        os.environ["VAULT_K8S_ROLE"] = "test-k8s-role"
        os.environ["VAULT_K8S_TOKEN_PATH"] = "/test/token/path"

        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.auth.kubernetes.login.return_value = {
            "auth": {"client_token": "k8s-token"}
        }
        mock_hvac_client.return_value = mock_client

        # Mock the token file
        mock_file = Mock()
        mock_file.read.return_value = "k8s-jwt-token"
        mock_open.return_value.__enter__.return_value = mock_file

        provider = VaultSecretsProvider()

        assert provider.client.token == "k8s-token"
        mock_client.auth.kubernetes.login.assert_called_once_with(
            role="test-k8s-role", jwt="k8s-jwt-token", mount_point="kubernetes"
        )

    @patch("app.providers.vault.hvac.Client")
    @patch("boto3.Session")
    def test_authenticate_with_aws(self, mock_boto_session, mock_hvac_client):
        """Test AWS IAM authentication."""
        os.environ["VAULT_AUTH_METHOD"] = "aws"
        os.environ["VAULT_AWS_ROLE"] = "test-aws-role"
        os.environ["AWS_ACCESS_KEY_ID"] = "test-access-key"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "test-secret-key"
        os.environ["AWS_DEFAULT_REGION"] = "us-west-2"

        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_client.auth.aws.iam_login.return_value = {
            "auth": {"client_token": "aws-token"}
        }
        mock_hvac_client.return_value = mock_client

        mock_session = Mock()
        mock_credentials = Mock()
        mock_credentials.access_key = "test-access-key"
        mock_credentials.secret_key = "test-secret-key"
        mock_credentials.token = None
        mock_session.get_credentials.return_value = mock_credentials
        mock_boto_session.return_value = mock_session

        provider = VaultSecretsProvider()

        assert provider.client.token == "aws-token"
        mock_client.auth.aws.iam_login.assert_called_once()

    @patch("app.providers.vault.hvac.Client")
    def test_secret_path_construction(self, mock_hvac_client):
        """Test secret path construction."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()

        ref = SecretRef("tenant-1", "prod", "api-key")
        path = provider._secret_path(ref)

        assert path == "secret/data/tenant-1/prod/api-key"

    @patch("app.providers.vault.hvac.Client")
    def test_get_secret_success(self, mock_hvac_client):
        """Test successful secret retrieval."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        # Mock the secret response
        mock_response = {
            "data": {
                "data": {"value": "secret-value"},
                "metadata": {
                    "version": 1,
                    "created_time": "2024-01-01T00:00:00Z",
                    "deletion_time": "",
                    "destroyed": False,
                },
            }
        }

        provider = VaultSecretsProvider()
        provider.client.secrets.kv.v2.read_secret_version = Mock(
            return_value=mock_response
        )

        ref = SecretRef("tenant-1", "prod", "api-key")
        value, metadata = provider.get_secret(ref)

        assert value == "secret-value"
        assert metadata["provider"] == "vault"
        assert metadata["version"] == "1"
        assert metadata["mount_point"] == "secret"

    @patch("app.providers.vault.hvac.Client")
    def test_get_secret_with_version(self, mock_hvac_client):
        """Test secret retrieval with specific version."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        mock_response = {
            "data": {
                "data": {"value": "versioned-secret"},
                "metadata": {
                    "version": 2,
                    "created_time": "2024-01-01T00:00:00Z",
                    "deletion_time": "",
                    "destroyed": False,
                },
            }
        }

        provider = VaultSecretsProvider()
        provider.client.secrets.kv.v2.read_secret_version = Mock(
            return_value=mock_response
        )

        ref = SecretRef("tenant-1", "prod", "api-key", version="2")
        value, metadata = provider.get_secret(ref)

        assert value == "versioned-secret"
        provider.client.secrets.kv.v2.read_secret_version.assert_called_once()

    @patch("app.providers.vault.hvac.Client")
    def test_get_secret_not_found(self, mock_hvac_client):
        """Test secret not found scenario."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()
        provider.client.secrets.kv.v2.read_secret_version = Mock(
            side_effect=Exception("Secret not found")
        )

        ref = SecretRef("tenant-1", "prod", "nonexistent")

        with pytest.raises(Exception):
            provider.get_secret(ref)

    @patch("app.providers.vault.hvac.Client")
    def test_get_secret_json_value(self, mock_hvac_client):
        """Test secret retrieval with JSON value."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        mock_response = {
            "data": {
                "data": {
                    "database_url": "postgres://...",
                    "api_key": "secret-key",
                    "timeout": 30,
                },
                "metadata": {
                    "version": 1,
                    "created_time": "2024-01-01T00:00:00Z",
                    "deletion_time": "",
                    "destroyed": False,
                },
            }
        }

        provider = VaultSecretsProvider()
        provider.client.secrets.kv.v2.read_secret_version = Mock(
            return_value=mock_response
        )

        ref = SecretRef("tenant-1", "prod", "config")
        value, metadata = provider.get_secret(ref)

        # Should return JSON string when multiple values
        parsed_value = json.loads(value)
        assert parsed_value["database_url"] == "postgres://..."
        assert parsed_value["api_key"] == "secret-key"

    @patch("app.providers.vault.hvac.Client")
    @patch("time.time")
    def test_rotate_secret_success(self, mock_time, mock_hvac_client):
        """Test successful secret rotation."""
        mock_time.return_value = 1234567890

        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()

        # Mock get_secret for current secret
        provider.get_secret = Mock(return_value=("old-secret-value", {"version": "1"}))

        # Mock create_or_update_secret
        provider.client.secrets.kv.v2.create_or_update_secret = Mock()

        # Mock get_secret for new secret
        provider.get_secret = Mock(
            side_effect=[
                ("old-secret-value", {"version": "1"}),
                ("new-secret-value", {"version": "2"}),
            ]
        )

        ref = SecretRef("tenant-1", "prod", "api-key")
        result = provider.rotate_secret(ref, reason="security_rotation")

        assert result["status"] == "success"
        assert result["previous_version"] == "1"
        assert result["new_version"] == "2"
        assert result["provider"] == "vault"

    @patch("app.providers.vault.hvac.Client")
    def test_rotate_secret_dry_run(self, mock_hvac_client):
        """Test secret rotation dry run."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()

        ref = SecretRef("tenant-1", "prod", "api-key")
        result = provider.rotate_secret(ref, dry_run=True)

        assert result["status"] == "dry_run"
        assert result["message"] == "Dry run - no rotation performed"

    @patch("app.providers.vault.hvac.Client")
    def test_list_secrets_success(self, mock_hvac_client):
        """Test successful secret listing."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        mock_response = {
            "data": {"keys": ["api-key", "database-password", "jwt-secret"]}
        }

        provider = VaultSecretsProvider()
        provider.client.secrets.kv.v2.list_secrets = Mock(return_value=mock_response)

        secrets = provider.list_secrets("tenant-1", "prod")

        assert secrets == ["api-key", "database-password", "jwt-secret"]

    @patch("app.providers.vault.hvac.Client")
    def test_list_secrets_empty(self, mock_hvac_client):
        """Test secret listing with no secrets."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()
        provider.client.secrets.kv.v2.list_secrets = Mock(
            side_effect=Exception("Path not found")
        )

        secrets = provider.list_secrets("tenant-1", "empty")

        assert secrets == []

    @patch("app.providers.vault.hvac.Client")
    def test_delete_secret_success(self, mock_hvac_client):
        """Test successful secret deletion."""
        mock_client = Mock()
        mock_client.is_authenticated.return_value = True
        mock_hvac_client.return_value = mock_client

        provider = VaultSecretsProvider()
        provider.client.secrets.kv.v2.delete_metadata_and_all_versions = Mock()

        ref = SecretRef("tenant-1", "prod", "api-key")
        result = provider.delete_secret(ref)

        assert result["status"] == "success"
        assert result["deleted"] is True
        assert result["provider"] == "vault"


class TestVaultProviderIntegration:
    """Test Vault provider integration with the dispatcher."""

    def setup_method(self):
        """Set up test environment."""
        # Clear any existing SECRETS_PROVIDER
        if "SECRETS_PROVIDER" in os.environ:
            del os.environ["SECRETS_PROVIDER"]

    def teardown_method(self):
        """Clean up environment."""
        for key in ["SECRETS_PROVIDER", "VAULT_TOKEN", "VAULT_AUTH_METHOD"]:
            if key in os.environ:
                del os.environ[key]

    @patch("app.providers.dispatcher.VaultSecretsProvider")
    def test_dispatcher_selects_vault_provider(self, mock_vault_provider):
        """Test that dispatcher selects Vault provider when configured."""
        os.environ["SECRETS_PROVIDER"] = "vault"

        mock_provider_instance = Mock()
        mock_vault_provider.return_value = mock_provider_instance

        from app.providers.dispatcher import get_provider

        provider = get_provider()

        assert provider == mock_provider_instance
        mock_vault_provider.assert_called_once()

    def test_vault_provider_environment_validation(self):
        """Test that Vault provider validates required environment variables."""
        # Clear any existing VAULT_TOKEN
        if "VAULT_TOKEN" in os.environ:
            del os.environ["VAULT_TOKEN"]

        os.environ["SECRETS_PROVIDER"] = "vault"
        os.environ["VAULT_AUTH_METHOD"] = "token"

        with pytest.raises(
            ValueError, match="VAULT_TOKEN environment variable is required"
        ):
            # Import and instantiate directly to avoid dispatcher module import issues
            from app.providers.vault import VaultSecretsProvider

            VaultSecretsProvider()


if __name__ == "__main__":
    pytest.main([__file__])
