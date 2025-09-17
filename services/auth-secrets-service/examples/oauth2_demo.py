#!/usr/bin/env python3
"""
Demo script for OAuth2 authorization flows.

This script demonstrates:
1. OAuth2 client registration
2. Authorization code flow with PKCE
3. Token exchange and refresh
4. Client credentials flow
5. Token revocation

Prerequisites:
- Auth & Secrets Service running on localhost:8011
- Valid JWT token for client registration
"""

import json
import requests
import secrets
import base64
import hashlib
from urllib.parse import urlencode, parse_qs, urlparse


class OAuth2Demo:
    """OAuth2 flow demonstration."""

    def __init__(self, base_url: str = "http://localhost:8011", jwt_token: str = None):
        """Initialize the demo."""
        self.base_url = base_url
        self.jwt_token = jwt_token
        self.session = requests.Session()

        if self.jwt_token:
            self.session.headers.update({"Authorization": f"Bearer {self.jwt_token}"})

    def generate_pkce_challenge(self):
        """Generate PKCE challenge and verifier."""
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32))
            .decode("ascii")
            .rstrip("=")
        )
        code_challenge = (
            base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode("ascii")).digest()
            )
            .decode("ascii")
            .rstrip("=")
        )

        return {
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

    def register_public_client(self, name: str, redirect_uri: str, scopes: list[str]):
        """Register a public OAuth2 client."""
        print(f"\n🔐 Registering public client: {name}")

        payload = {
            "name": name,
            "description": f"Demo client: {name}",
            "client_type": "public",
            "redirect_uris": [redirect_uri],
            "allowed_scopes": scopes,
        }

        response = self.session.post(f"{self.base_url}/oauth2/clients", json=payload)

        if response.status_code == 200:
            client = response.json()
            print(f"✅ Client registered successfully!")
            print(f"   Client ID: {client['client_id']}")
            print(f"   Type: {client['client_type']}")
            print(f"   Redirect URIs: {client['redirect_uris']}")
            print(f"   Allowed Scopes: {client['allowed_scopes']}")
            return client
        else:
            print(f"❌ Client registration failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def register_confidential_client(
        self, name: str, redirect_uri: str, scopes: list[str]
    ):
        """Register a confidential OAuth2 client."""
        print(f"\n🔐 Registering confidential client: {name}")

        payload = {
            "name": name,
            "description": f"Demo confidential client: {name}",
            "client_type": "confidential",
            "redirect_uris": [redirect_uri],
            "allowed_scopes": scopes,
        }

        response = self.session.post(f"{self.base_url}/oauth2/clients", json=payload)

        if response.status_code == 200:
            client = response.json()
            print(f"✅ Confidential client registered successfully!")
            print(f"   Client ID: {client['client_id']}")
            print(f"   Client Secret: {client['client_secret']}")
            print(f"   Type: {client['client_type']}")
            print(f"   Redirect URIs: {client['redirect_uris']}")
            print(f"   Allowed Scopes: {client['allowed_scopes']}")
            return client
        else:
            print(f"❌ Client registration failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def list_clients(self):
        """List registered OAuth2 clients."""
        print(f"\n📋 Listing OAuth2 clients...")

        response = self.session.get(f"{self.base_url}/oauth2/clients")

        if response.status_code == 200:
            clients = response.json()
            print(f"✅ Found {len(clients)} clients:")
            for client in clients:
                print(
                    f"   - {client['name']} ({client['client_type']}) - {client['client_id']}"
                )
            return clients
        else:
            print(f"❌ Failed to list clients: {response.status_code}")
            print(f"   Error: {response.text}")
            return []

    def generate_pkce_challenge_endpoint(self):
        """Generate PKCE challenge using the service endpoint."""
        print(f"\n🔑 Generating PKCE challenge...")

        response = self.session.get(f"{self.base_url}/oauth2/pkce/challenge")

        if response.status_code == 200:
            challenge = response.json()
            print(f"✅ PKCE challenge generated!")
            print(f"   Code Verifier: {challenge['code_verifier']}")
            print(f"   Code Challenge: {challenge['code_challenge']}")
            print(f"   Method: {challenge['code_challenge_method']}")
            return challenge
        else:
            print(f"❌ Failed to generate PKCE challenge: {response.status_code}")
            return None

    def build_authorization_url(
        self,
        client_id: str,
        redirect_uri: str,
        scopes: list[str],
        code_challenge: str,
        state: str = None,
    ):
        """Build authorization URL."""
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }

        if state:
            params["state"] = state

        return f"{self.base_url}/oauth2/authorize?{urlencode(params)}"

    def exchange_code_for_token(
        self,
        client_id: str,
        code: str,
        redirect_uri: str,
        code_verifier: str = None,
        client_secret: str = None,
    ):
        """Exchange authorization code for access token."""
        print(f"\n🔄 Exchanging authorization code for token...")

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": client_id,
        }

        if code_verifier:
            data["code_verifier"] = code_verifier

        if client_secret:
            data["client_secret"] = client_secret

        response = self.session.post(f"{self.base_url}/oauth2/token", data=data)

        if response.status_code == 200:
            token_response = response.json()
            print(f"✅ Token exchange successful!")
            print(f"   Access Token: {token_response['access_token'][:20]}...")
            print(f"   Token Type: {token_response['token_type']}")
            print(f"   Expires In: {token_response['expires_in']} seconds")
            if token_response.get("refresh_token"):
                print(f"   Refresh Token: {token_response['refresh_token'][:20]}...")
            if token_response.get("scope"):
                print(f"   Scope: {token_response['scope']}")
            return token_response
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def refresh_access_token(
        self, client_id: str, refresh_token: str, client_secret: str = None
    ):
        """Refresh access token using refresh token."""
        print(f"\n🔄 Refreshing access token...")

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
        }

        if client_secret:
            data["client_secret"] = client_secret

        response = self.session.post(f"{self.base_url}/oauth2/token", data=data)

        if response.status_code == 200:
            token_response = response.json()
            print(f"✅ Token refresh successful!")
            print(f"   New Access Token: {token_response['access_token'][:20]}...")
            print(f"   Token Type: {token_response['token_type']}")
            print(f"   Expires In: {token_response['expires_in']} seconds")
            if token_response.get("refresh_token"):
                print(
                    f"   New Refresh Token: {token_response['refresh_token'][:20]}..."
                )
            return token_response
        else:
            print(f"❌ Token refresh failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def client_credentials_flow(
        self, client_id: str, client_secret: str, scopes: list[str]
    ):
        """Client credentials flow for server-to-server authentication."""
        print(f"\n🔄 Client credentials flow...")

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "scope": " ".join(scopes),
        }

        if client_secret:
            data["client_secret"] = client_secret

        response = self.session.post(f"{self.base_url}/oauth2/token", data=data)

        if response.status_code == 200:
            token_response = response.json()
            print(f"✅ Client credentials flow successful!")
            print(f"   Access Token: {token_response['access_token'][:20]}...")
            print(f"   Token Type: {token_response['token_type']}")
            print(f"   Expires In: {token_response['expires_in']} seconds")
            if token_response.get("scope"):
                print(f"   Scope: {token_response['scope']}")
            return token_response
        else:
            print(f"❌ Client credentials flow failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None


def main():
    """Run OAuth2 demo."""
    print("🔐 OAuth2 Authorization Flows Demo")
    print("=" * 50)

    # Initialize demo
    demo = OAuth2Demo()

    # Note: For full demo, you need a JWT token for client registration
    # For this demo, we'll show the flow structure

    print("\n📝 OAuth2 Flow Demo Structure:")
    print("1. Register OAuth2 clients (requires JWT token)")
    print("2. Generate PKCE challenge for public clients")
    print("3. Build authorization URL")
    print("4. Exchange authorization code for tokens")
    print("5. Refresh access tokens")
    print("6. Client credentials flow")

    # Generate PKCE challenge (no auth required)
    pkce_challenge = demo.generate_pkce_challenge_endpoint()

    if pkce_challenge:
        # Show how to build authorization URL
        print(f"\n🔗 Example Authorization URL:")
        auth_url = demo.build_authorization_url(
            client_id="demo-client",
            redirect_uri="https://example.com/callback",
            scopes=["read", "write"],
            code_challenge=pkce_challenge["code_challenge"],
            state="demo-state-123",
        )
        print(f"   {auth_url}")

    print(f"\n💡 To run full demo:")
    print("1. Start the auth-secrets-service")
    print("2. Get a JWT token with client:manage permission")
    print("3. Run: python oauth2_demo.py --token YOUR_JWT_TOKEN")
    print("4. Follow the interactive prompts")

    print(f"\n📚 OAuth2 Endpoints:")
    print(f"   POST /oauth2/clients - Register client")
    print(f"   GET /oauth2/clients - List clients")
    print(f"   GET /oauth2/pkce/challenge - Generate PKCE challenge")
    print(f"   GET /oauth2/authorize - Authorization endpoint")
    print(f"   POST /oauth2/token - Token endpoint")


if __name__ == "__main__":
    main()
