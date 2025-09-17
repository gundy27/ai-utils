"""Tests for audit logging functionality."""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.audit.models import (
    AuditEvent,
    AuditEventType,
    AuditQuery,
    AuditResult,
    create_audit_event,
    create_auth_event,
    create_secret_event,
)
from app.audit.storage import AuditStorage


class TestAuditModels:
    """Test audit model functionality."""

    def test_audit_event_creation(self):
        """Test creating audit events."""
        event = create_audit_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.SUCCESS,
            actor_id="user-123",
            tenant_id="tenant-1",
            action="fetch_secret",
            description="Secret fetched successfully",
            resource_type="secret",
            resource_id="prod/api-key",
            metadata={"secret_name": "API_KEY", "scope": "prod"},
        )

        assert event.event_type == AuditEventType.SECRET_FETCH
        assert event.result == AuditResult.SUCCESS
        assert event.actor_id == "user-123"
        assert event.tenant_id == "tenant-1"
        assert event.action == "fetch_secret"
        assert event.description == "Secret fetched successfully"
        assert event.resource_type == "secret"
        assert event.resource_id == "prod/api-key"
        assert event.metadata["secret_name"] == "API_KEY"
        assert event.metadata["scope"] == "prod"
        assert event.event_id is not None
        assert event.timestamp is not None

    def test_auth_event_creation(self):
        """Test creating authentication events."""
        event = create_auth_event(
            event_type=AuditEventType.AUTH_TOKEN_ISSUED,
            result=AuditResult.SUCCESS,
            actor_id="user-456",
            tenant_id="tenant-2",
            token_info={"token_id": "jwt-789", "subject": "user-456"},
        )

        assert event.event_type == AuditEventType.AUTH_TOKEN_ISSUED
        assert event.result == AuditResult.SUCCESS
        assert event.actor_id == "user-456"
        assert event.tenant_id == "tenant-2"
        assert event.resource_type == "auth"
        assert "jwt-789" in event.description
        assert event.metadata["token_id"] == "jwt-789"

    def test_secret_event_creation(self):
        """Test creating secret events."""
        event = create_secret_event(
            event_type=AuditEventType.SECRET_ROTATE,
            result=AuditResult.SUCCESS,
            actor_id="user-789",
            tenant_id="tenant-3",
            secret_ref="prod/db-password",
            scope="prod",
            secret_name="DB_PASSWORD",
        )

        assert event.event_type == AuditEventType.SECRET_ROTATE
        assert event.result == AuditResult.SUCCESS
        assert event.actor_id == "user-789"
        assert event.tenant_id == "tenant-3"
        assert event.resource_type == "secret"
        assert event.resource_id == "prod/db-password"
        assert event.resource_scope == "prod"
        assert "prod/DB_PASSWORD" in event.description


class TestAuditStorage:
    """Test audit storage functionality."""

    def setup_method(self):
        """Set up test storage."""
        self.storage = AuditStorage(max_events=1000)

    def test_store_and_retrieve_event(self):
        """Test storing and retrieving audit events."""
        event = create_audit_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.SUCCESS,
            actor_id="user-123",
            tenant_id="tenant-1",
            action="fetch_secret",
            description="Test event",
        )

        # Store event
        self.storage.store_event(event)

        # Query events
        query = AuditQuery(tenant_id="tenant-1")
        response = self.storage.query_events(query)

        assert len(response.events) == 1
        assert response.events[0].event_id == event.event_id
        assert response.total_count == 1
        assert response.page == 1
        assert response.page_size == 50

    def test_filter_by_event_type(self):
        """Test filtering events by type."""
        # Create events of different types
        event1 = create_audit_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.SUCCESS,
            actor_id="user-1",
            tenant_id="tenant-1",
            action="fetch",
            description="Fetch event",
        )

        event2 = create_audit_event(
            event_type=AuditEventType.AUTH_TOKEN_ISSUED,
            result=AuditResult.SUCCESS,
            actor_id="user-1",
            tenant_id="tenant-1",
            action="issue",
            description="Issue event",
        )

        self.storage.store_event(event1)
        self.storage.store_event(event2)

        # Filter by event type
        query = AuditQuery(
            tenant_id="tenant-1", event_types=[AuditEventType.SECRET_FETCH]
        )
        response = self.storage.query_events(query)

        assert len(response.events) == 1
        assert response.events[0].event_type == AuditEventType.SECRET_FETCH

    def test_filter_by_result(self):
        """Test filtering events by result."""
        # Create events with different results
        event1 = create_audit_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.SUCCESS,
            actor_id="user-1",
            tenant_id="tenant-1",
            action="fetch",
            description="Success event",
        )

        event2 = create_audit_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.FAILURE,
            actor_id="user-1",
            tenant_id="tenant-1",
            action="fetch",
            description="Failure event",
        )

        self.storage.store_event(event1)
        self.storage.store_event(event2)

        # Filter by result
        query = AuditQuery(tenant_id="tenant-1", results=[AuditResult.SUCCESS])
        response = self.storage.query_events(query)

        assert len(response.events) == 1
        assert response.events[0].result == AuditResult.SUCCESS

    def test_filter_by_actor(self):
        """Test filtering events by actor."""
        # Create events with different actors
        event1 = create_audit_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.SUCCESS,
            actor_id="user-1",
            tenant_id="tenant-1",
            action="fetch",
            description="User 1 event",
        )

        event2 = create_audit_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.SUCCESS,
            actor_id="user-2",
            tenant_id="tenant-1",
            action="fetch",
            description="User 2 event",
        )

        self.storage.store_event(event1)
        self.storage.store_event(event2)

        # Filter by actor
        query = AuditQuery(tenant_id="tenant-1", actor_id="user-1")
        response = self.storage.query_events(query)

        assert len(response.events) == 1
        assert response.events[0].actor_id == "user-1"

    def test_pagination(self):
        """Test pagination functionality."""
        # Create multiple events
        events = []
        for i in range(25):
            event = create_audit_event(
                event_type=AuditEventType.SECRET_FETCH,
                result=AuditResult.SUCCESS,
                actor_id=f"user-{i}",
                tenant_id="tenant-1",
                action="fetch",
                description=f"Event {i}",
            )
            events.append(event)
            self.storage.store_event(event)

        # Test first page
        query = AuditQuery(tenant_id="tenant-1", page=1, page_size=10)
        response = self.storage.query_events(query)

        assert len(response.events) == 10
        assert response.total_count == 25
        assert response.total_pages == 3
        assert response.has_next is True
        assert response.has_previous is False

        # Test second page
        query.page = 2
        response = self.storage.query_events(query)

        assert len(response.events) == 10
        assert response.has_next is True
        assert response.has_previous is True

        # Test last page
        query.page = 3
        response = self.storage.query_events(query)

        assert len(response.events) == 5
        assert response.has_next is False
        assert response.has_previous is True

    def test_tenant_stats(self):
        """Test tenant statistics."""
        # Create events with different results
        for i in range(10):
            result = AuditResult.SUCCESS if i % 2 == 0 else AuditResult.FAILURE
            event = create_audit_event(
                event_type=AuditEventType.SECRET_FETCH,
                result=result,
                actor_id=f"user-{i % 3}",  # 3 unique actors
                tenant_id="tenant-1",
                action="fetch",
                description=f"Event {i}",
                resource_id=f"resource-{i % 2}",  # 2 unique resources
            )
            self.storage.store_event(event)

        stats = self.storage.get_tenant_stats("tenant-1", days=30)

        assert stats["total_events"] == 10
        assert stats["successful_events"] == 5
        assert stats["failed_events"] == 5
        assert stats["unique_actors"] == 3
        assert stats["unique_resources"] == 2

    def test_export_events(self):
        """Test event export functionality."""
        # Create test events
        event = create_audit_event(
            event_type=AuditEventType.SECRET_FETCH,
            result=AuditResult.SUCCESS,
            actor_id="user-123",
            tenant_id="tenant-1",
            action="fetch_secret",
            description="Test export event",
        )
        self.storage.store_event(event)

        # Export as JSON
        json_data = self.storage.export_events("tenant-1", "json")
        assert json_data is not None
        assert "user-123" in json_data
        assert "secret.fetch" in json_data

        # Export as CSV
        csv_data = self.storage.export_events("tenant-1", "csv")
        assert csv_data is not None
        assert "user-123" in csv_data
        assert "secret.fetch" in csv_data
        assert csv_data.startswith("event_id,timestamp")


class TestAuditIntegration:
    """Test audit integration with API endpoints."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_audit_logs_endpoint_without_auth(self):
        """Test that audit logs endpoint requires authentication."""
        response = self.client.get("/audit/logs", params={"tenant_id": "tenant-1"})
        assert response.status_code == 401

    def test_audit_stats_endpoint_without_auth(self):
        """Test that audit stats endpoint requires authentication."""
        response = self.client.get("/audit/stats", params={"tenant_id": "tenant-1"})
        assert response.status_code == 401

    def test_audit_export_endpoint_without_auth(self):
        """Test that audit export endpoint requires authentication."""
        response = self.client.get("/audit/export", params={"tenant_id": "tenant-1"})
        assert response.status_code == 401


class TestAuditEventTypes:
    """Test all audit event types."""

    def test_all_event_types_defined(self):
        """Test that all expected event types are defined."""
        expected_types = [
            "auth.login",
            "auth.logout",
            "auth.login_failed",
            "auth.token_issued",
            "auth.token_validated",
            "auth.token_expired",
            "auth.token_invalid",
            "secret.fetch",
            "secret.fetch_failed",
            "secret.rotate",
            "secret.rotate_failed",
            "secret.delete",
            "secret.delete_failed",
            "access.granted",
            "access.denied",
            "permission.check",
            "tenant.access",
            "user.created",
            "user.updated",
            "user.deleted",
            "role.assigned",
            "role.revoked",
            "tenant.created",
            "tenant.updated",
            "system.startup",
            "system.shutdown",
            "config.changed",
            "error.occurred",
        ]

        for event_type in expected_types:
            assert hasattr(AuditEventType, event_type.upper().replace(".", "_"))

    def test_all_result_types_defined(self):
        """Test that all expected result types are defined."""
        expected_results = ["success", "failure", "denied", "error"]

        for result in expected_results:
            assert hasattr(AuditResult, result.upper())


if __name__ == "__main__":
    pytest.main([__file__])
