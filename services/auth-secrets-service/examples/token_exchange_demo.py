#!/usr/bin/env python3
"""
Demo script for Token Exchange and Delegation functionality.

This script demonstrates:
1. Token exchange for scope/audience changes
2. Token delegation for microservices
3. User impersonation for admin operations
4. Delegation policy management
5. Audit logging and monitoring

Prerequisites:
- Auth & Secrets Service running on localhost:8011
- Valid JWT token with appropriate permissions
"""

import json
import requests
import secrets
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


class TokenExchangeDemo:
    """Token exchange and delegation demonstration."""

    def __init__(self, base_url: str = "http://localhost:8011", jwt_token: str = None):
        """Initialize the demo."""
        self.base_url = base_url
        self.jwt_token = jwt_token
        self.session = requests.Session()

        if self.jwt_token:
            self.session.headers.update({"Authorization": f"Bearer {self.jwt_token}"})

    def exchange_token(
        self,
        subject_token: str,
        subject_token_type: str = "urn:ietf:params:oauth:token-type:access_token",
        audience: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Exchange a token for different scopes/audience."""
        print(f"\n🔄 Token Exchange")
        print(f"   Subject Token: {subject_token[:20]}...")
        print(f"   Audience: {audience or 'default'}")
        print(f"   Scope: {scope or 'unchanged'}")

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
            "subject_token": subject_token,
            "subject_token_type": subject_token_type,
            "requested_token_type": "urn:ietf:params:oauth:token-type:access_token",
        }

        if audience:
            data["audience"] = audience
        if scope:
            data["scope"] = scope

        response = self.session.post(f"{self.base_url}/token-exchange/token", data=data)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Token exchange successful!")
            print(f"   New Access Token: {result['access_token'][:20]}...")
            print(f"   Token Type: {result['token_type']}")
            print(f"   Expires In: {result['expires_in']} seconds")
            if result.get("scope"):
                print(f"   Scope: {result['scope']}")
            return result
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def delegate_token(
        self,
        source_token: str,
        target_audience: str,
        target_scopes: list[str],
        delegation_chain: list[str] = None,
        impersonation: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Delegate a token to another service."""
        print(f"\n🔗 Token Delegation")
        print(f"   Source Token: {source_token[:20]}...")
        print(f"   Target Audience: {target_audience}")
        print(f"   Target Scopes: {target_scopes}")
        print(f"   Impersonation: {impersonation}")

        payload = {
            "source_token": source_token,
            "target_audience": target_audience,
            "target_scopes": target_scopes,
            "impersonation": impersonation,
            "delegation_chain": delegation_chain or [],
            "expires_in": 3600,
            "metadata": {
                "delegation_reason": "Microservice communication",
                "source_service": "api-gateway",
                "target_service": target_audience,
            },
        }

        response = self.session.post(
            f"{self.base_url}/token-exchange/delegate", json=payload
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Token delegation successful!")
            print(f"   Delegated Token: {result['delegated_token'][:20]}...")
            print(f"   Token Type: {result['token_type']}")
            print(f"   Expires In: {result['expires_in']} seconds")
            print(f"   Scope: {result['scope']}")
            print(f"   Audience: {result['audience']}")
            print(f"   Delegation Chain: {result['delegation_chain']}")
            return result
        else:
            print(f"❌ Token delegation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def impersonate_user(
        self,
        source_token: str,
        target_user_id: str,
        target_tenant_id: str,
        target_scopes: list[str],
        impersonation_reason: str,
    ) -> Optional[Dict[str, Any]]:
        """Impersonate another user (admin operation)."""
        print(f"\n👤 User Impersonation")
        print(f"   Source Token: {source_token[:20]}...")
        print(f"   Target User: {target_user_id}")
        print(f"   Target Tenant: {target_tenant_id}")
        print(f"   Reason: {impersonation_reason}")
        print(f"   Target Scopes: {target_scopes}")

        payload = {
            "source_token": source_token,
            "target_user_id": target_user_id,
            "target_tenant_id": target_tenant_id,
            "impersonation_reason": impersonation_reason,
            "target_scopes": target_scopes,
            "expires_in": 1800,  # 30 minutes for impersonation
            "metadata": {"admin_operation": True, "support_request": True},
        }

        response = self.session.post(
            f"{self.base_url}/token-exchange/impersonate", json=payload
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ User impersonation successful!")
            print(f"   Impersonation Token: {result['impersonation_token'][:20]}...")
            print(f"   Token Type: {result['token_type']}")
            print(f"   Expires In: {result['expires_in']} seconds")
            print(f"   Scope: {result['scope']}")
            print(f"   Impersonated User: {result['impersonated_user_id']}")
            print(f"   Impersonated Tenant: {result['impersonated_tenant_id']}")
            return result
        else:
            print(f"❌ User impersonation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def create_delegation_policy(
        self,
        policy_id: str,
        name: str,
        source_scopes: list[str],
        target_scopes: list[str],
        allowed_audiences: list[str] = None,
        max_delegation_depth: int = 3,
        requires_impersonation_permission: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Create a delegation policy."""
        print(f"\n📋 Create Delegation Policy")
        print(f"   Policy ID: {policy_id}")
        print(f"   Name: {name}")
        print(f"   Source Scopes: {source_scopes}")
        print(f"   Target Scopes: {target_scopes}")
        print(f"   Allowed Audiences: {allowed_audiences or 'any'}")
        print(f"   Max Delegation Depth: {max_delegation_depth}")

        payload = {
            "policy_id": policy_id,
            "name": name,
            "description": f"Demo delegation policy: {name}",
            "source_scopes": source_scopes,
            "target_scopes": target_scopes,
            "allowed_audiences": allowed_audiences or [],
            "max_delegation_depth": max_delegation_depth,
            "requires_impersonation_permission": requires_impersonation_permission,
            "expires_in_override": None,
            "conditions": {
                "time_restriction": "business_hours",
                "ip_whitelist": ["192.168.1.0/24"],
            },
        }

        response = self.session.post(
            f"{self.base_url}/token-exchange/policies", json=payload
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Delegation policy created successfully!")
            print(f"   Policy ID: {result['policy_id']}")
            print(f"   Name: {result['name']}")
            print(f"   Tenant ID: {result['tenant_id']}")
            print(f"   Max Delegation Depth: {result['max_delegation_depth']}")
            print(
                f"   Requires Impersonation: {result['requires_impersonation_permission']}"
            )
            return result
        else:
            print(f"❌ Delegation policy creation failed: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def list_delegation_policies(self) -> list[Dict[str, Any]]:
        """List delegation policies."""
        print(f"\n📋 Listing Delegation Policies...")

        response = self.session.get(f"{self.base_url}/token-exchange/policies")

        if response.status_code == 200:
            policies = response.json()
            print(f"✅ Found {len(policies)} delegation policies:")
            for policy in policies:
                print(f"   - {policy['name']} ({policy['policy_id']})")
                print(f"     Source: {policy['source_scopes']}")
                print(f"     Target: {policy['target_scopes']}")
                print(f"     Max Depth: {policy['max_delegation_depth']}")
            return policies
        else:
            print(f"❌ Failed to list policies: {response.status_code}")
            print(f"   Error: {response.text}")
            return []

    def get_delegation_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific delegation policy."""
        print(f"\n📋 Get Delegation Policy: {policy_id}")

        response = self.session.get(
            f"{self.base_url}/token-exchange/policies/{policy_id}"
        )

        if response.status_code == 200:
            policy = response.json()
            print(f"✅ Policy retrieved successfully!")
            print(f"   Name: {policy['name']}")
            print(f"   Description: {policy.get('description', 'N/A')}")
            print(f"   Source Scopes: {policy['source_scopes']}")
            print(f"   Target Scopes: {policy['target_scopes']}")
            print(f"   Allowed Audiences: {policy['allowed_audiences']}")
            print(f"   Max Delegation Depth: {policy['max_delegation_depth']}")
            print(
                f"   Requires Impersonation: {policy['requires_impersonation_permission']}"
            )
            return policy
        else:
            print(f"❌ Failed to get policy: {response.status_code}")
            print(f"   Error: {response.text}")
            return None

    def get_audit_events(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Get token exchange audit events."""
        print(f"\n📊 Token Exchange Audit Events")

        response = self.session.get(
            f"{self.base_url}/token-exchange/audit/events", params={"limit": limit}
        )

        if response.status_code == 200:
            events = response.json()
            print(f"✅ Found {len(events)} audit events:")
            for event in events:
                print(f"   - {event['event_type']} by {event['actor_id']}")
                print(f"     Tenant: {event['tenant_id']}")
                print(f"     Success: {event['success']}")
                print(f"     Timestamp: {event['timestamp']}")
                if event.get("audience"):
                    print(f"     Audience: {event['audience']}")
                if event.get("delegation_chain"):
                    print(f"     Delegation Chain: {event['delegation_chain']}")
            return events
        else:
            print(f"❌ Failed to get audit events: {response.status_code}")
            print(f"   Error: {response.text}")
            return []

    def get_audit_stats(self) -> Dict[str, Any]:
        """Get token exchange audit statistics."""
        print(f"\n📊 Token Exchange Audit Statistics")

        response = self.session.get(f"{self.base_url}/token-exchange/audit/stats")

        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Audit statistics:")
            print(f"   Total Events: {stats['total_events']}")
            print(f"   Successful Exchanges: {stats['successful_exchanges']}")
            print(f"   Failed Exchanges: {stats['failed_exchanges']}")
            print(f"   Delegation Events: {stats['delegation_events']}")
            print(f"   Impersonation Events: {stats['impersonation_events']}")
            return stats
        else:
            print(f"❌ Failed to get audit stats: {response.status_code}")
            print(f"   Error: {response.text}")
            return {}


def main():
    """Run token exchange demo."""
    print("🔄 Token Exchange & Delegation Demo")
    print("=" * 50)

    # Initialize demo
    demo = TokenExchangeDemo()

    print("\n📝 Token Exchange Flow Demo Structure:")
    print("1. Create delegation policies")
    print("2. Exchange tokens for different scopes/audiences")
    print("3. Delegate tokens to microservices")
    print("4. Impersonate users (admin operations)")
    print("5. Monitor audit events and statistics")

    print(f"\n💡 To run full demo:")
    print("1. Start the auth-secrets-service")
    print("2. Get a JWT token with delegation/impersonation permissions")
    print("3. Run: python token_exchange_demo.py --token YOUR_JWT_TOKEN")
    print("4. Follow the interactive prompts")

    print(f"\n📚 Token Exchange Endpoints:")
    print(f"   POST /token-exchange/token - Exchange token")
    print(f"   POST /token-exchange/delegate - Delegate token")
    print(f"   POST /token-exchange/impersonate - Impersonate user")
    print(f"   POST /token-exchange/policies - Create delegation policy")
    print(f"   GET /token-exchange/policies - List policies")
    print(f"   GET /token-exchange/audit/events - Get audit events")
    print(f"   GET /token-exchange/audit/stats - Get statistics")


if __name__ == "__main__":
    main()
