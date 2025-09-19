"""Example demonstrating audit functionality in the downloader."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.downloader import (
    CompositeAuditHook,
    DownloadAuditQuery,
    FileAuditHook,
    HTTPSource,
    LoggingAuditHook,
    UniversalDownloader,
)


async def main():
    """Demonstrate audit functionality."""
    print("🔍 Downloader Audit Example")
    print("=" * 50)

    # Create a temporary directory for downloads and audit logs
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        downloads_dir = temp_path / "downloads"
        audit_file = temp_path / "audit.jsonl"

        print(f"📁 Working directory: {temp_dir}")
        print(f"📁 Downloads directory: {downloads_dir}")
        print(f"📄 Audit log file: {audit_file}")
        print()

        # 1. Create audit hooks
        print("🔧 Setting up audit hooks...")

        # File-based audit hook for persistent storage
        file_audit_hook = FileAuditHook(audit_file)

        # Logging audit hook for real-time monitoring
        logging_audit_hook = LoggingAuditHook(log_level="info")

        # Composite hook that sends events to both
        audit_hook = CompositeAuditHook([file_audit_hook, logging_audit_hook])

        print("✅ Audit hooks configured")
        print()

        # 2. Create downloader with audit hook
        print("🚀 Creating downloader with audit support...")
        downloader = UniversalDownloader(
            max_retries=2,
            timeout_seconds=30,
            destination_directory=str(downloads_dir),
            audit_hook=audit_hook,
        )
        print("✅ Downloader created with audit logging enabled")
        print()

        # 3. Perform downloads with audit logging
        print("📥 Performing downloads with audit logging...")

        # Download a sample PDF
        http_source = HTTPSource(
            identifier="sample_pdf",
            url="https://www.africau.edu/images/default/sample.pdf",
            headers={"User-Agent": "GundyAIDownloader-AuditExample/1.0"},
        )

        result = await downloader.download(
            source=http_source,
            actor_id="demo_user",
            tenant_id="demo_tenant",
            session_id="demo_session_123",
        )

        if result.success:
            print(f"✅ Download successful: {result.local_file.path}")
            print(f"   Size: {result.bytes_downloaded} bytes")
            print(f"   Time: {result.download_time_seconds:.2f}s")
            print(f"   Checksum: {result.local_file.checksum.value}")
        else:
            print(f"❌ Download failed: {result.error}")
        print()

        # 4. Query audit events
        print("🔍 Querying audit events...")

        # Query all events for our tenant
        query = DownloadAuditQuery(
            tenant_id="demo_tenant",
            limit=10,
        )

        audit_result = await audit_hook.query_audit_events(query)

        print(f"📊 Found {audit_result.total_count} audit events:")
        for event in audit_result.events:
            print(
                f"   - {event.event_type}: {event.source_identifier} by {event.actor_id}"
            )
            print(f"     Success: {event.success}, Size: {event.file_size} bytes")
            print(f"     Time: {event.timestamp}")
        print()

        # 5. Get audit statistics
        print("📈 Getting audit statistics...")

        stats = await audit_hook.get_audit_stats("demo_tenant")

        print("📊 Audit Statistics for tenant 'demo_tenant':")
        print(f"   Total events: {stats.total_events}")
        print(f"   Successful downloads: {stats.successful_downloads}")
        print(f"   Failed downloads: {stats.failed_downloads}")
        print(f"   Average download time: {stats.average_download_time_ms:.2f} ms")
        print(f"   Total bytes downloaded: {stats.total_bytes_downloaded}")

        if stats.event_type_counts:
            print("   Event types:")
            for event_type, count in stats.event_type_counts.items():
                print(f"     - {event_type}: {count}")
        print()

        # 6. Demonstrate batch downloads with audit
        print("📦 Performing batch downloads with audit logging...")

        # Create multiple sources
        sources = [
            HTTPSource(
                identifier="sample_doc1",
                url="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
            ),
            HTTPSource(
                identifier="sample_doc2",
                url="https://www.learningcontainer.com/wp-content/uploads/2019/09/sample-pdf-file.pdf",
            ),
        ]

        batch_results = await downloader.download_multiple(
            sources=sources,
            actor_id="batch_user",
            tenant_id="demo_tenant",
            session_id="batch_session_456",
        )

        successful = sum(1 for r in batch_results.values() if r.success)
        print(f"📊 Batch download completed: {successful}/{len(sources)} successful")

        for identifier, result in batch_results.items():
            if result.success:
                print(f"   ✅ {identifier}: {result.local_file.path}")
            else:
                print(f"   ❌ {identifier}: {result.error}")
        print()

        # 7. Final audit statistics
        print("📈 Final audit statistics...")

        final_stats = await audit_hook.get_audit_stats("demo_tenant")

        print("📊 Final Statistics:")
        print(f"   Total events: {final_stats.total_events}")
        print(f"   Successful downloads: {final_stats.successful_downloads}")
        print(f"   Failed downloads: {final_stats.failed_downloads}")
        print(
            f"   Average download time: {final_stats.average_download_time_ms:.2f} ms"
        )
        print(f"   Total bytes downloaded: {final_stats.total_bytes_downloaded}")

        if final_stats.top_actors:
            print("   Top actors:")
            for actor in final_stats.top_actors[:3]:
                print(f"     - {actor['actor_id']}: {actor['count']} events")
        print()

        # 8. Show audit file contents
        print("📄 Audit log file contents:")
        if audit_file.exists():
            with open(audit_file) as f:
                lines = f.readlines()
                print(f"   {len(lines)} audit events logged to {audit_file}")

                # Show a sample event
                if lines:
                    import json

                    sample_event = json.loads(lines[0])
                    print("   Sample event:")
                    print(f"     Type: {sample_event.get('audit_event_type')}")
                    print(f"     Actor: {sample_event.get('actor_id')}")
                    print(f"     Tenant: {sample_event.get('tenant_id')}")
                    print(f"     Success: {sample_event.get('success')}")
                    print(f"     Timestamp: {sample_event.get('timestamp')}")
        else:
            print("   No audit file found")
        print()

    print("🎉 Audit example completed!")
    print("\n💡 Key takeaways:")
    print("   - All download operations are automatically audited")
    print("   - Audit events include actor, tenant, and operation details")
    print("   - Multiple audit hooks can be used simultaneously")
    print("   - Audit data can be queried and analyzed")
    print("   - Statistics provide insights into download patterns")


if __name__ == "__main__":
    asyncio.run(main())
