"""Tests for audit functionality."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gundy_ai.downloader.audit import (
    DownloadAuditEvent,
    DownloadAuditEventType,
    DownloadAuditQuery,
    DownloadAuditResult,
    DownloadAuditSeverity,
    create_download_audit_event,
    create_suspicious_activity_event,
)
from gundy_ai.downloader.audit_hooks import (
    AuditHook,
    CompositeAuditHook,
    FileAuditHook,
    LoggingAuditHook,
    NoOpAuditHook,
)
from gundy_ai.downloader.base import SourceType


class TestDownloadAuditEvent:
    """Test DownloadAuditEvent model."""

    def test_create_basic_audit_event(self):
        """Test creating a basic audit event."""
        event = create_download_audit_event(
            event_type=DownloadAuditEventType.DOWNLOAD_START,
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            source_uri="https://example.com/file.pdf",
            destination_path="/tmp/downloads/file.pdf",
            success=True,
        )

        assert event.event_type == DownloadAuditEventType.DOWNLOAD_START
        assert event.actor_id == "user123"
        assert event.tenant_id == "tenant456"
        assert event.source_identifier == "source789"
        assert event.source_type == SourceType.HTTP
        assert event.source_uri == "https://example.com/file.pdf"
        assert event.destination_path == "/tmp/downloads/file.pdf"
        assert event.success is True
        assert event.severity == DownloadAuditSeverity.INFO
        assert event.timestamp is not None

    def test_create_suspicious_activity_event(self):
        """Test creating a suspicious activity event."""
        event = create_suspicious_activity_event(
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            reason="Multiple failed authentication attempts",
            metadata={"attempts": 5, "ip_address": "192.168.1.100"},
        )

        assert event.event_type == DownloadAuditEventType.SUSPICIOUS_ACTIVITY
        assert event.actor_id == "user123"
        assert event.tenant_id == "tenant456"
        assert event.source_identifier == "source789"
        assert event.source_type == SourceType.HTTP
        assert event.success is False
        assert event.severity == DownloadAuditSeverity.WARNING
        assert "security" in event.tags
        assert "security_incident" in event.compliance_flags
        assert event.metadata["attempts"] == 5
        assert event.metadata["ip_address"] == "192.168.1.100"

    def test_audit_event_serialization(self):
        """Test audit event JSON serialization."""
        event = create_download_audit_event(
            event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            source_uri="https://example.com/file.pdf",
            destination_path="/tmp/downloads/file.pdf",
            success=True,
            file_size=1024,
            bytes_downloaded=1024,
            download_duration_ms=500.0,
        )

        # Test dict conversion
        event_dict = event.dict()
        assert event_dict["event_type"] == "download_success"
        assert event_dict["actor_id"] == "user123"
        assert event_dict["file_size"] == 1024
        assert event_dict["bytes_downloaded"] == 1024
        assert event_dict["download_duration_ms"] == 500.0

        # Test JSON serialization
        json_str = event.json()
        parsed_event = DownloadAuditEvent.parse_raw(json_str)
        assert parsed_event.event_type == event.event_type
        assert parsed_event.actor_id == event.actor_id
        assert parsed_event.file_size == event.file_size


class TestDownloadAuditQuery:
    """Test DownloadAuditQuery model."""

    def test_create_basic_query(self):
        """Test creating a basic audit query."""
        query = DownloadAuditQuery(
            tenant_id="tenant123",
            event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
            success=True,
            limit=50,
        )

        assert query.tenant_id == "tenant123"
        assert query.event_type == DownloadAuditEventType.DOWNLOAD_SUCCESS
        assert query.success is True
        assert query.limit == 50
        assert query.offset == 0  # default value
        assert query.sort_by == "timestamp"  # default value
        assert query.sort_order == "desc"  # default value

    def test_query_with_time_range(self):
        """Test query with time range."""
        start_time = datetime.utcnow() - timedelta(hours=24)
        end_time = datetime.utcnow()

        query = DownloadAuditQuery(
            start_time=start_time,
            end_time=end_time,
            limit=100,
        )

        assert query.start_time == start_time
        assert query.end_time == end_time
        assert query.limit == 100


class TestNoOpAuditHook:
    """Test NoOpAuditHook."""

    @pytest.mark.asyncio
    async def test_log_event_no_op(self):
        """Test that NoOpAuditHook discards events."""
        hook = NoOpAuditHook()
        event = create_download_audit_event(
            event_type=DownloadAuditEventType.DOWNLOAD_START,
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            source_uri="https://example.com/file.pdf",
            destination_path="/tmp/downloads/file.pdf",
            success=True,
        )

        # Should not raise any exceptions
        await hook.log_download_event(event)

    @pytest.mark.asyncio
    async def test_query_events_empty(self):
        """Test that NoOpAuditHook returns empty results."""
        hook = NoOpAuditHook()
        query = DownloadAuditQuery()

        result = await hook.query_audit_events(query)

        assert result.events == []
        assert result.total_count == 0
        assert result.has_more is False

    @pytest.mark.asyncio
    async def test_get_stats_empty(self):
        """Test that NoOpAuditHook returns empty stats."""
        hook = NoOpAuditHook()

        stats = await hook.get_audit_stats("tenant123")

        assert stats.tenant_id == "tenant123"
        assert stats.total_events == 0
        assert stats.successful_downloads == 0
        assert stats.failed_downloads == 0


class TestLoggingAuditHook:
    """Test LoggingAuditHook."""

    @pytest.mark.asyncio
    async def test_log_event_to_structured_logs(self):
        """Test that LoggingAuditHook logs events to structured logs."""
        with patch("gundy_ai.downloader.audit_hooks.logger") as mock_logger:
            hook = LoggingAuditHook(log_level="info")
            event = create_download_audit_event(
                event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
                actor_id="user123",
                tenant_id="tenant456",
                source_identifier="source789",
                source_type=SourceType.HTTP,
                source_uri="https://example.com/file.pdf",
                destination_path="/tmp/downloads/file.pdf",
                success=True,
                file_size=1024,
            )

            await hook.log_download_event(event)

            # Verify that the logger was called with the expected data
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "download_audit_event" in call_args[0]
            assert call_args[1]["audit_event_id"] == event.event_id
            assert call_args[1]["actor_id"] == "user123"
            assert call_args[1]["tenant_id"] == "tenant456"
            assert call_args[1]["file_size"] == 1024

    @pytest.mark.asyncio
    async def test_query_events_not_supported(self):
        """Test that LoggingAuditHook doesn't support querying."""
        with patch("gundy_ai.downloader.audit_hooks.logger") as mock_logger:
            hook = LoggingAuditHook()
            query = DownloadAuditQuery()

            result = await hook.query_audit_events(query)

            assert result.events == []
            assert result.total_count == 0
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stats_not_supported(self):
        """Test that LoggingAuditHook doesn't support statistics."""
        with patch("gundy_ai.downloader.audit_hooks.logger") as mock_logger:
            hook = LoggingAuditHook()

            stats = await hook.get_audit_stats("tenant123")

            assert stats.tenant_id == "tenant123"
            assert stats.total_events == 0
            mock_logger.warning.assert_called_once()


class TestFileAuditHook:
    """Test FileAuditHook."""

    @pytest.fixture
    def temp_audit_file(self):
        """Create a temporary audit file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            temp_file = Path(f.name)
        yield temp_file
        temp_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_log_event_to_file(self, temp_audit_file):
        """Test that FileAuditHook stores events in a file."""
        hook = FileAuditHook(temp_audit_file)
        event = create_download_audit_event(
            event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            source_uri="https://example.com/file.pdf",
            destination_path="/tmp/downloads/file.pdf",
            success=True,
            file_size=1024,
        )

        await hook.log_download_event(event)
        await hook._flush_buffer()  # Force flush

        # Verify file was created and contains the event
        assert temp_audit_file.exists()
        with open(temp_audit_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            stored_event = json.loads(lines[0])
            assert stored_event["actor_id"] == "user123"
            assert stored_event["tenant_id"] == "tenant456"
            assert stored_event["file_size"] == 1024

    @pytest.mark.asyncio
    async def test_query_events_from_file(self, temp_audit_file):
        """Test querying events from file."""
        hook = FileAuditHook(temp_audit_file)

        # Create and store multiple events
        events = []
        for i in range(3):
            event = create_download_audit_event(
                event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
                actor_id=f"user{i}",
                tenant_id="tenant456",
                source_identifier=f"source{i}",
                source_type=SourceType.HTTP,
                source_uri=f"https://example.com/file{i}.pdf",
                destination_path=f"/tmp/downloads/file{i}.pdf",
                success=True,
            )
            events.append(event)
            await hook.log_download_event(event)

        await hook._flush_buffer()  # Force flush

        # Query all events
        query = DownloadAuditQuery(tenant_id="tenant456")
        result = await hook.query_audit_events(query)

        assert len(result.events) == 3
        assert result.total_count == 3
        assert result.has_more is False

        # Query with filter
        query = DownloadAuditQuery(actor_id="user1")
        result = await hook.query_audit_events(query)

        assert len(result.events) == 1
        assert result.events[0].actor_id == "user1"

    @pytest.mark.asyncio
    async def test_get_stats_from_file(self, temp_audit_file):
        """Test getting statistics from file."""
        hook = FileAuditHook(temp_audit_file)

        # Create and store events with different types
        events = [
            create_download_audit_event(
                event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
                actor_id="user1",
                tenant_id="tenant456",
                source_identifier="source1",
                source_type=SourceType.HTTP,
                source_uri="https://example.com/file1.pdf",
                destination_path="/tmp/downloads/file1.pdf",
                success=True,
                file_size=1024,
                bytes_downloaded=1024,
                download_duration_ms=500.0,
            ),
            create_download_audit_event(
                event_type=DownloadAuditEventType.DOWNLOAD_FAILURE,
                actor_id="user2",
                tenant_id="tenant456",
                source_identifier="source2",
                source_type=SourceType.HTTP,
                source_uri="https://example.com/file2.pdf",
                destination_path="/tmp/downloads/file2.pdf",
                success=False,
            ),
        ]

        for event in events:
            await hook.log_download_event(event)

        await hook._flush_buffer()  # Force flush

        stats = await hook.get_audit_stats("tenant456")

        assert stats.tenant_id == "tenant456"
        assert stats.total_events == 2
        assert stats.successful_downloads == 1
        assert stats.failed_downloads == 1
        assert stats.average_download_time_ms == 500.0
        assert stats.total_bytes_downloaded == 1024
        assert "download_success" in stats.event_type_counts
        assert "download_failure" in stats.event_type_counts
        assert stats.event_type_counts["download_success"] == 1
        assert stats.event_type_counts["download_failure"] == 1

    @pytest.mark.asyncio
    async def test_file_rotation(self, temp_audit_file):
        """Test file rotation when size limit is exceeded."""
        # Create a hook with very small file size limit
        hook = FileAuditHook(temp_audit_file, max_file_size_mb=0.001)  # 1KB limit

        # Write a large event to trigger rotation
        event = create_download_audit_event(
            event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            source_uri="https://example.com/file.pdf",
            destination_path="/tmp/downloads/file.pdf",
            success=True,
            metadata={"large_data": "x" * 2000},  # Large metadata to exceed 1KB
        )

        await hook.log_download_event(event)
        await hook._flush_buffer()

        # Verify that the original file was rotated
        assert not temp_audit_file.exists()
        # Should have created a rotated file with timestamp
        rotated_files = list(
            temp_audit_file.parent.glob(f"{temp_audit_file.stem}.*.jsonl")
        )
        assert len(rotated_files) == 1


class TestCompositeAuditHook:
    """Test CompositeAuditHook."""

    @pytest.mark.asyncio
    async def test_forward_to_multiple_hooks(self):
        """Test that CompositeAuditHook forwards events to multiple hooks."""
        mock_hook1 = AsyncMock(spec=AuditHook)
        mock_hook2 = AsyncMock(spec=AuditHook)

        hook = CompositeAuditHook([mock_hook1, mock_hook2])
        event = create_download_audit_event(
            event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            source_uri="https://example.com/file.pdf",
            destination_path="/tmp/downloads/file.pdf",
            success=True,
        )

        await hook.log_download_event(event)

        # Verify both hooks received the event
        mock_hook1.log_download_event.assert_called_once_with(event)
        mock_hook2.log_download_event.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_query_from_first_available_hook(self):
        """Test that CompositeAuditHook queries from first available hook."""
        mock_hook1 = AsyncMock(spec=AuditHook)
        mock_hook2 = AsyncMock(spec=AuditHook)

        # Mock hook1 to return empty results, hook2 to return data
        mock_hook1.query_audit_events.return_value = DownloadAuditResult(
            events=[], total_count=0, has_more=False, query=DownloadAuditQuery()
        )

        test_event = create_download_audit_event(
            event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            source_uri="https://example.com/file.pdf",
            destination_path="/tmp/downloads/file.pdf",
            success=True,
        )

        mock_hook2.query_audit_events.return_value = DownloadAuditResult(
            events=[test_event],
            total_count=1,
            has_more=False,
            query=DownloadAuditQuery(),
        )

        hook = CompositeAuditHook([mock_hook1, mock_hook2])
        query = DownloadAuditQuery()

        result = await hook.query_audit_events(query)

        # Should return results from hook2 (first non-empty)
        assert len(result.events) == 1
        assert result.events[0].actor_id == "user123"
        mock_hook1.query_audit_events.assert_called_once_with(query)
        mock_hook2.query_audit_events.assert_called_once_with(query)

    @pytest.mark.asyncio
    async def test_handle_hook_failures(self):
        """Test that CompositeAuditHook handles individual hook failures gracefully."""
        mock_hook1 = AsyncMock(spec=AuditHook)
        mock_hook2 = AsyncMock(spec=AuditHook)

        # Mock hook1 to raise an exception
        mock_hook1.log_download_event.side_effect = Exception("Hook1 failed")
        mock_hook2.log_download_event.return_value = None

        hook = CompositeAuditHook([mock_hook1, mock_hook2])
        event = create_download_audit_event(
            event_type=DownloadAuditEventType.DOWNLOAD_SUCCESS,
            actor_id="user123",
            tenant_id="tenant456",
            source_identifier="source789",
            source_type=SourceType.HTTP,
            source_uri="https://example.com/file.pdf",
            destination_path="/tmp/downloads/file.pdf",
            success=True,
        )

        # Should not raise exception even if one hook fails
        await hook.log_download_event(event)

        # Both hooks should have been called
        mock_hook1.log_download_event.assert_called_once_with(event)
        mock_hook2.log_download_event.assert_called_once_with(event)


class TestAuditIntegration:
    """Test audit integration with downloader components."""

    @pytest.mark.asyncio
    async def test_audit_logging_in_download_flow(self):
        """Test that audit events are logged during download flow."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_file = Path(temp_dir) / "audit.jsonl"
            hook = FileAuditHook(audit_file)

            # Create a mock source
            mock_source = MagicMock()
            mock_source.identifier = "test_source"
            mock_source.source_type = SourceType.HTTP
            mock_source.get_uri.return_value = "https://example.com/test.pdf"

            # Create a mock downloader with audit hook
            from gundy_ai.downloader.base import BaseDownloader

            class TestDownloader(BaseDownloader):
                async def download(self, source, destination, **kwargs):
                    from gundy_ai.downloader.base import (
                        DownloadResult,
                        FileChecksum,
                        LocalFile,
                    )

                    # Mock successful download
                    local_file = LocalFile(
                        path=Path(destination),
                        checksum=FileChecksum(
                            algorithm="sha256", value="test_hash", size_bytes=100
                        ),
                    )
                    return DownloadResult.success_result(
                        local_file=local_file,
                        bytes_downloaded=100,
                        download_time_seconds=1.0,
                    )

                def can_handle(self, source):
                    return True

            downloader = TestDownloader(audit_hook=hook)
            destination = Path(temp_dir) / "test_file.pdf"

            # Perform download with audit logging
            result = await downloader.download_with_retry(
                source=mock_source,
                destination=destination,
                actor_id="test_user",
                tenant_id="test_tenant",
            )

            # Verify download was successful
            assert result.success

            # Force flush and verify audit events were logged
            await hook._flush_buffer()

            assert audit_file.exists()
            with open(audit_file) as f:
                lines = f.readlines()
                assert len(lines) >= 1  # At least download_start event

                # Parse events and verify content
                events = [json.loads(line) for line in lines]
                event_types = [event["audit_event_type"] for event in events]

                assert "download_start" in event_types
                assert "download_success" in event_types

                # Verify actor and tenant information
                for event in events:
                    assert event["actor_id"] == "test_user"
                    assert event["tenant_id"] == "test_tenant"
                    assert event["source_identifier"] == "test_source"
