"""Basic usage example for gundy-ai-job-queue."""

import asyncio

from gundy_ai.job_queue import InMemoryQueue


async def process_document(payload):
    """Simulate document processing."""
    await asyncio.sleep(0.1)  # Simulate work
    return {"processed": payload["file"], "chunks": 10}


async def main():
    """Demonstrate basic job queue usage."""

    print("=== Gundy AI Job Queue - Basic Usage ===\n")

    # Create queue
    queue = InMemoryQueue()

    print("✓ Queue initialized\n")

    # 1. Enqueue jobs
    print("1. Enqueueing jobs...")

    job1 = await queue.enqueue(
        job_type="document_ingest",
        payload={"file": "doc1.pdf"},
        idempotency_key="doc1",
        priority=0,
    )

    job2 = await queue.enqueue(
        job_type="document_ingest",
        payload={"file": "doc2.pdf"},
        idempotency_key="doc2",
        priority=10,  # Higher priority
    )

    job3 = await queue.enqueue(
        job_type="document_ingest",
        payload={"file": "doc3.pdf"},
        priority=5,
    )

    print(f"   Job 1: {job1.id} (priority: 0)")
    print(f"   Job 2: {job2.id} (priority: 10)")
    print(f"   Job 3: {job3.id} (priority: 5)\n")

    # 2. Check stats
    print("2. Queue statistics...")
    stats = await queue.get_stats()

    print(f"   Total jobs: {stats.total_jobs}")
    print(f"   Queued: {stats.queued}")
    print(f"   Processing: {stats.processing}\n")

    # 3. Process jobs
    print("3. Processing jobs (priority order)...")

    async def worker():
        """Worker to process jobs."""
        count = 0
        async for job in queue.process():
            print(f"\n   Processing: {job.id}")
            print(f"     Type: {job.job_type}")
            print(f"     Payload: {job.payload}")
            print(f"     Attempt: {job.attempts}")

            try:
                # Process the job
                result = await process_document(job.payload)
                await queue.complete(job.id, result=result)
                print(f"     ✓ Completed: {result}")
            except Exception as e:
                await queue.fail(job.id, error=str(e))
                print(f"     ✗ Failed: {e}")

            count += 1
            if count == 3:  # Process 3 jobs then stop
                break

    await worker()

    print("\n4. Final statistics...")
    stats = await queue.get_stats()

    print(f"   Total jobs: {stats.total_jobs}")
    print(f"   Queued: {stats.queued}")
    print(f"   Completed: {stats.completed}")
    print(f"   Failed: {stats.failed}\n")

    # 5. Test idempotency
    print("5. Testing idempotency...")
    duplicate = await queue.enqueue(
        job_type="document_ingest",
        payload={"file": "DIFFERENT.pdf"},
        idempotency_key="doc1",  # Same key as job1
    )

    print("   Tried to enqueue duplicate with same idempotency key")
    print(f"   Returned existing job: {duplicate.id == job1.id}")
    print(f"   Original payload preserved: {duplicate.payload == job1.payload}\n")

    print("✓ All operations complete!")


if __name__ == "__main__":
    asyncio.run(main())
