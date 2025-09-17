#!/usr/bin/env python3
"""Demo script showing audit logging functionality."""

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.audit.models import (
    AuditEventType,
    AuditResult,
    create_audit_event,
    create_auth_event,
    create_secret_event,
)
from app.audit.storage import AuditStorage


def demo_audit_event_creation():
    """Demonstrate creating different types of audit events."""
    print("=== Audit Event Creation Demo ===\n")

    # Create a secret fetch event
    secret_event = create_secret_event(
        event_type=AuditEventType.SECRET_FETCH,
        result=AuditResult.SUCCESS,
        actor_id="user-123",
        tenant_id="acme-corp",
        secret_ref="prod/api-key",
        scope="prod",
        secret_name="API_KEY",
    )

    print("Secret Fetch Event:")
    print(f"  Event ID: {secret_event.event_id}")
    print(f"  Type: {secret_event.event_type}")
    print(f"  Result: {secret_event.result}")
    print(f"  Actor: {secret_event.actor_id}")
    print(f"  Tenant: {secret_event.tenant_id}")
    print(f"  Description: {secret_event.description}")
    print(f"  Resource: {secret_event.resource_type}/{secret_event.resource_id}")
    print(f"  Timestamp: {secret_event.timestamp}")
    print()

    # Create an authentication event
    auth_event = create_auth_event(
        event_type=AuditEventType.AUTH_TOKEN_ISSUED,
        result=AuditResult.SUCCESS,
        actor_id="admin-456",
        tenant_id="acme-corp",
        token_info={
            "token_id": "jwt-789",
            "subject": "user-123",
            "audience": "api-service",
            "expires_in": 3600,
        },
    )

    print("Authentication Event:")
    print(f"  Event ID: {auth_event.event_id}")
    print(f"  Type: {auth_event.event_type}")
    print(f"  Result: {auth_event.result}")
    print(f"  Actor: {auth_event.actor_id}")
    print(f"  Tenant: {auth_event.tenant_id}")
    print(f"  Description: {auth_event.description}")
    print(f"  Metadata: {auth_event.metadata}")
    print()

    # Create a custom audit event
    custom_event = create_audit_event(
        event_type=AuditEventType.ACCESS_DENIED,
        result=AuditResult.DENIED,
        actor_id="user-999",
        tenant_id="competitor-corp",
        action="unauthorized_access_attempt",
        description="Attempted to access restricted resource",
        resource_type="secret",
        resource_id="prod/database-password",
        metadata={
            "attempted_action": "secret.fetch",
            "ip_address": "192.168.1.100",
            "user_agent": "curl/7.68.0",
        },
        tags=["security", "unauthorized_access"],
    )

    print("Custom Access Denied Event:")
    print(f"  Event ID: {custom_event.event_id}")
    print(f"  Type: {custom_event.event_type}")
    print(f"  Result: {custom_event.result}")
    print(f"  Actor: {custom_event.actor_id}")
    print(f"  Tenant: {custom_event.tenant_id}")
    print(f"  Description: {custom_event.description}")
    print(f"  Tags: {custom_event.tags}")
    print(f"  Metadata: {custom_event.metadata}")
    print()


def demo_audit_storage():
    """Demonstrate audit storage functionality."""
    print("=== Audit Storage Demo ===\n")

    # Create storage instance
    storage = AuditStorage(max_events=100)

    # Store various events
    events_to_store = [
        create_secret_event(
            AuditEventType.SECRET_FETCH,
            AuditResult.SUCCESS,
            "user-1",
            "tenant-a",
            "prod/api-key",
            "prod",
            "API_KEY",
        ),
        create_secret_event(
            AuditEventType.SECRET_ROTATE,
            AuditResult.SUCCESS,
            "admin-1",
            "tenant-a",
            "prod/db-password",
            "prod",
            "DB_PASSWORD",
        ),
        create_auth_event(
            AuditEventType.AUTH_TOKEN_ISSUED,
            AuditResult.SUCCESS,
            "admin-1",
            "tenant-a",
        ),
        create_secret_event(
            AuditEventType.SECRET_FETCH,
            AuditResult.FAILURE,
            "user-2",
            "tenant-a",
            "prod/nonexistent",
            "prod",
            "NONEXISTENT",
        ),
        create_auth_event(
            AuditEventType.AUTH_TOKEN_INVALID,
            AuditResult.FAILURE,
            "user-3",
            "tenant-b",
        ),
    ]

    print(f"Storing {len(events_to_store)} events...")
    for event in events_to_store:
        storage.store_event(event)
        print(f"  ✓ Stored {event.event_type} for {event.actor_id}")

    print(f"\nStorage Stats:")
    stats = storage.get_storage_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    print("\n" + "=" * 50 + "\n")


def demo_audit_querying():
    """Demonstrate audit querying functionality."""
    print("=== Audit Querying Demo ===\n")

    # Create storage with sample data
    storage = AuditStorage(max_events=100)

    # Generate sample events
    import random

    for i in range(20):
        event_type = random.choice(
            [
                AuditEventType.SECRET_FETCH,
                AuditEventType.SECRET_ROTATE,
                AuditEventType.AUTH_TOKEN_ISSUED,
                AuditEventType.AUTH_TOKEN_VALIDATED,
            ]
        )

        result = random.choice([AuditResult.SUCCESS, AuditResult.FAILURE])
        actor_id = f"user-{random.randint(1, 5)}"
        tenant_id = random.choice(["tenant-a", "tenant-b"])

        if event_type in [AuditEventType.SECRET_FETCH, AuditEventType.SECRET_ROTATE]:
            event = create_secret_event(
                event_type,
                result,
                actor_id,
                tenant_id,
                f"scope{i}/secret{i}",
                f"scope{i}",
                f"SECRET_{i}",
            )
        else:
            event = create_auth_event(
                event_type,
                result,
                actor_id,
                tenant_id,
            )

        storage.store_event(event)

    print("Sample data generated. Querying...")

    # Query 1: All events for tenant-a
    from app.audit.models import AuditQuery

    query = AuditQuery(tenant_id="tenant-a")
    response = storage.query_events(query)

    print(f"\n1. All events for tenant-a:")
    print(f"   Total: {response.total_count} events")
    print(f"   Page: {response.page}/{response.total_pages}")
    print(f"   Events on this page: {len(response.events)}")

    for event in response.events[:3]:  # Show first 3
        print(f"     - {event.event_type} by {event.actor_id} ({event.result})")

    # Query 2: Only successful events
    query = AuditQuery(tenant_id="tenant-a", results=[AuditResult.SUCCESS])
    response = storage.query_events(query)

    print(f"\n2. Successful events for tenant-a:")
    print(f"   Total: {response.total_count} events")

    # Query 3: Events by specific actor
    query = AuditQuery(tenant_id="tenant-a", actor_id="user-1")
    response = storage.query_events(query)

    print(f"\n3. Events by user-1 for tenant-a:")
    print(f"   Total: {response.total_count} events")

    # Query 4: Secret-related events only
    query = AuditQuery(
        tenant_id="tenant-a",
        event_types=[AuditEventType.SECRET_FETCH, AuditEventType.SECRET_ROTATE],
    )
    response = storage.query_events(query)

    print(f"\n4. Secret events for tenant-a:")
    print(f"   Total: {response.total_count} events")

    # Query 5: With pagination
    query = AuditQuery(tenant_id="tenant-a", page=1, page_size=5)
    response = storage.query_events(query)

    print(f"\n5. First 5 events for tenant-a:")
    print(f"   Page: {response.page}/{response.total_pages}")
    print(f"   Has next: {response.has_next}")
    print(f"   Has previous: {response.has_previous}")

    for event in response.events:
        print(f"     - {event.event_type} by {event.actor_id} ({event.result})")

    print("\n" + "=" * 50 + "\n")


def demo_audit_statistics():
    """Demonstrate audit statistics functionality."""
    print("=== Audit Statistics Demo ===\n")

    # Create storage with sample data
    storage = AuditStorage(max_events=100)

    # Generate events with known patterns
    for i in range(50):
        # Create a mix of successful and failed events
        result = AuditResult.SUCCESS if i % 3 != 0 else AuditResult.FAILURE

        # Use 3 different actors
        actor_id = f"user-{i % 3 + 1}"

        # Use 2 different tenants
        tenant_id = "tenant-a" if i % 2 == 0 else "tenant-b"

        # Create event
        event = create_secret_event(
            AuditEventType.SECRET_FETCH,
            result,
            actor_id,
            tenant_id,
            f"scope{i % 5}/secret{i}",
            f"scope{i % 5}",
            f"SECRET_{i}",
        )

        storage.store_event(event)

    # Get statistics for tenant-a
    stats_a = storage.get_tenant_stats("tenant-a", days=30)
    print("Statistics for tenant-a (last 30 days):")
    print(f"  Total events: {stats_a['total_events']}")
    print(f"  Successful events: {stats_a['successful_events']}")
    print(f"  Failed events: {stats_a['failed_events']}")
    print(f"  Unique actors: {stats_a['unique_actors']}")
    print(f"  Unique resources: {stats_a['unique_resources']}")
    print()

    # Get statistics for tenant-b
    stats_b = storage.get_tenant_stats("tenant-b", days=30)
    print("Statistics for tenant-b (last 30 days):")
    print(f"  Total events: {stats_b['total_events']}")
    print(f"  Successful events: {stats_b['successful_events']}")
    print(f"  Failed events: {stats_b['failed_events']}")
    print(f"  Unique actors: {stats_b['unique_actors']}")
    print(f"  Unique resources: {stats_b['unique_resources']}")
    print()

    # Export data
    print("Exporting audit data...")
    json_data = storage.export_events("tenant-a", "json")
    print(f"  JSON export size: {len(json_data)} characters")

    csv_data = storage.export_events("tenant-a", "csv")
    print(f"  CSV export size: {len(csv_data)} characters")
    print(f"  CSV lines: {csv_data.count(chr(10)) + 1}")


def demo_event_types():
    """Demonstrate all audit event types."""
    print("=== Audit Event Types Demo ===\n")

    print("Available audit event types:")
    for event_type in AuditEventType:
        print(f"  - {event_type.value}")

    print(f"\nTotal event types: {len(list(AuditEventType))}")

    print("\nAvailable result types:")
    for result in AuditResult:
        print(f"  - {result.value}")

    print(f"\nTotal result types: {len(list(AuditResult))}")


def main():
    """Run all demos."""
    print("Audit Logging System Demo")
    print("=" * 60)
    print()

    demo_audit_event_creation()
    demo_audit_storage()
    demo_audit_querying()
    demo_audit_statistics()
    demo_event_types()

    print("Demo completed!")
    print("\nKey Features Demonstrated:")
    print("✓ Comprehensive audit event models")
    print("✓ In-memory storage with thread safety")
    print("✓ Advanced querying and filtering")
    print("✓ Pagination support")
    print("✓ Statistics and analytics")
    print("✓ Data export (JSON/CSV)")
    print("✓ Compliance-ready audit trails")


if __name__ == "__main__":
    main()
