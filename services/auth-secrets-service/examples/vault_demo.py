#!/usr/bin/env python3
"""
Demo script for HashiCorp Vault provider integration.

This script demonstrates:
1. Different Vault authentication methods
2. Secret operations (get, list, rotate, delete)
3. Environment configuration
4. Error handling

Prerequisites:
- HashiCorp Vault server running (dev mode is fine for testing)
- Appropriate authentication credentials configured
- KV v2 secrets engine enabled at 'secret' mount point
"""

import os
import sys
import json
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "app"))

from providers.vault import VaultSecretsProvider
from providers.base import SecretRef


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'='*60}")
    print(f" {title}")
    print("=" * 60)


def demo_token_authentication():
    """Demo token-based authentication."""
    print_section("Token Authentication Demo")

    # Set up environment for token authentication
    os.environ.update(
        {
            "VAULT_ADDR": "http://localhost:8200",
            "VAULT_AUTH_METHOD": "token",
            "VAULT_TOKEN": "hvs.xxxxxxxxxxxxxxxxxxxxxxxxx",  # Replace with actual token
            "VAULT_MOUNT_POINT": "secret",
            "VAULT_SKIP_VERIFY": "true",  # For dev mode
        }
    )

    try:
        provider = VaultSecretsProvider()
        print("✅ Vault provider initialized with token authentication")

        # Test secret operations
        ref = SecretRef("demo-tenant", "prod", "api-key")

        # Get secret
        try:
            value, metadata = provider.get_secret(ref)
            print(f"✅ Retrieved secret: {value[:10]}...")
            print(f"   Metadata: {json.dumps(metadata, indent=2)}")
        except KeyError as e:
            print(f"ℹ️  Secret not found (expected for demo): {e}")

        # List secrets
        secrets = provider.list_secrets("demo-tenant", "prod")
        print(f"✅ Listed secrets: {secrets}")

    except Exception as e:
        print(f"❌ Token authentication failed: {e}")


def demo_approle_authentication():
    """Demo AppRole authentication."""
    print_section("AppRole Authentication Demo")

    # Set up environment for AppRole authentication
    os.environ.update(
        {
            "VAULT_ADDR": "http://localhost:8200",
            "VAULT_AUTH_METHOD": "approle",
            "VAULT_ROLE_ID": "your-role-id",  # Replace with actual role ID
            "VAULT_SECRET_ID": "your-secret-id",  # Replace with actual secret ID
            "VAULT_APPROLE_MOUNT": "approle",
            "VAULT_MOUNT_POINT": "secret",
            "VAULT_SKIP_VERIFY": "true",
        }
    )

    try:
        provider = VaultSecretsProvider()
        print("✅ Vault provider initialized with AppRole authentication")

    except Exception as e:
        print(f"❌ AppRole authentication failed: {e}")


def demo_kubernetes_authentication():
    """Demo Kubernetes authentication."""
    print_section("Kubernetes Authentication Demo")

    # Set up environment for Kubernetes authentication
    os.environ.update(
        {
            "VAULT_ADDR": "http://localhost:8200",
            "VAULT_AUTH_METHOD": "kubernetes",
            "VAULT_K8S_ROLE": "your-k8s-role",  # Replace with actual role
            "VAULT_K8S_TOKEN_PATH": "/var/run/secrets/kubernetes.io/serviceaccount/token",
            "VAULT_K8S_MOUNT": "kubernetes",
            "VAULT_MOUNT_POINT": "secret",
            "VAULT_SKIP_VERIFY": "true",
        }
    )

    try:
        provider = VaultSecretsProvider()
        print("✅ Vault provider initialized with Kubernetes authentication")

    except Exception as e:
        print(f"❌ Kubernetes authentication failed: {e}")


def demo_aws_authentication():
    """Demo AWS IAM authentication."""
    print_section("AWS IAM Authentication Demo")

    # Set up environment for AWS authentication
    os.environ.update(
        {
            "VAULT_ADDR": "http://localhost:8200",
            "VAULT_AUTH_METHOD": "aws",
            "VAULT_AWS_ROLE": "your-aws-role",  # Replace with actual role
            "AWS_ACCESS_KEY_ID": "your-access-key",  # Replace with actual key
            "AWS_SECRET_ACCESS_KEY": "your-secret-key",  # Replace with actual key
            "AWS_DEFAULT_REGION": "us-east-1",
            "VAULT_AWS_MOUNT": "aws",
            "VAULT_MOUNT_POINT": "secret",
            "VAULT_SKIP_VERIFY": "true",
        }
    )

    try:
        provider = VaultSecretsProvider()
        print("✅ Vault provider initialized with AWS IAM authentication")

    except Exception as e:
        print(f"❌ AWS authentication failed: {e}")


def demo_secret_operations():
    """Demo various secret operations."""
    print_section("Secret Operations Demo")

    # Use token auth for this demo
    os.environ.update(
        {
            "VAULT_ADDR": "http://localhost:8200",
            "VAULT_AUTH_METHOD": "token",
            "VAULT_TOKEN": "hvs.xxxxxxxxxxxxxxxxxxxxxxxxx",  # Replace with actual token
            "VAULT_MOUNT_POINT": "secret",
            "VAULT_SKIP_VERIFY": "true",
        }
    )

    try:
        provider = VaultSecretsProvider()

        # Demo secret path construction
        ref = SecretRef("demo-tenant", "prod", "api-key")
        path = provider._secret_path(ref)
        print(f"✅ Secret path: {path}")

        # Demo secret retrieval
        try:
            value, metadata = provider.get_secret(ref)
            print(f"✅ Secret value: {value[:20]}...")
            print(f"   Version: {metadata.get('version')}")
            print(f"   Created: {metadata.get('created_time')}")
        except KeyError:
            print("ℹ️  Secret not found (this is expected for demo)")

        # Demo secret listing
        secrets = provider.list_secrets("demo-tenant", "prod")
        print(f"✅ Available secrets: {secrets}")

        # Demo secret rotation (dry run)
        result = provider.rotate_secret(ref, reason="demo_rotation", dry_run=True)
        print(f"✅ Rotation dry run result: {result}")

        # Demo secret deletion (would fail in real scenario without proper permissions)
        try:
            result = provider.delete_secret(ref)
            print(f"✅ Deletion result: {result}")
        except Exception as e:
            print(f"ℹ️  Deletion failed (expected): {e}")

    except Exception as e:
        print(f"❌ Secret operations failed: {e}")


def demo_environment_configuration():
    """Demo environment configuration options."""
    print_section("Environment Configuration Options")

    config_options = {
        "VAULT_ADDR": "Vault server URL (default: http://localhost:8200)",
        "VAULT_SKIP_VERIFY": "Skip SSL verification (default: false)",
        "VAULT_MOUNT_POINT": "KV secrets engine mount point (default: secret)",
        "VAULT_AUTH_METHOD": "Authentication method: token, approle, kubernetes, aws",
        # Token authentication
        "VAULT_TOKEN": "Vault token for token authentication",
        # AppRole authentication
        "VAULT_ROLE_ID": "AppRole role ID",
        "VAULT_SECRET_ID": "AppRole secret ID",
        "VAULT_APPROLE_MOUNT": "AppRole mount point (default: approle)",
        # Kubernetes authentication
        "VAULT_K8S_ROLE": "Kubernetes role name",
        "VAULT_K8S_TOKEN_PATH": "Path to Kubernetes service account token",
        "VAULT_K8S_MOUNT": "Kubernetes mount point (default: kubernetes)",
        # AWS authentication
        "VAULT_AWS_ROLE": "AWS IAM role name",
        "AWS_ACCESS_KEY_ID": "AWS access key ID",
        "AWS_SECRET_ACCESS_KEY": "AWS secret access key",
        "AWS_DEFAULT_REGION": "AWS region (default: us-east-1)",
        "VAULT_AWS_MOUNT": "AWS mount point (default: aws)",
    }

    print("Available environment variables:")
    for var, description in config_options.items():
        print(f"  {var}: {description}")


def main():
    """Run all demos."""
    print("🔐 HashiCorp Vault Provider Demo")
    print(
        "This demo shows how to use the Vault provider with different authentication methods."
    )
    print(
        "\nNote: Replace placeholder values with actual credentials for real testing."
    )

    # Show configuration options
    demo_environment_configuration()

    # Demo different authentication methods
    demo_token_authentication()
    demo_approle_authentication()
    demo_kubernetes_authentication()
    demo_aws_authentication()

    # Demo secret operations
    demo_secret_operations()

    print_section("Demo Complete")
    print("For production use:")
    print("1. Set up a real Vault server with proper security")
    print("2. Configure appropriate authentication methods")
    print("3. Set up KV v2 secrets engine")
    print("4. Create proper policies and roles")
    print("5. Use environment variables or secure configuration management")


if __name__ == "__main__":
    main()
