"""Tests for in-memory job queue."""

import asyncio

import pytest

from gundy_ai.job_queue import InMemoryQueue, JobStatus


@pytest.fixture
def queue():
    """Create in-memory queue."""
    return InMemoryQueue()


@pytest.mark.asyncio
async def test_enqueue_job(queue):
    """Test enqueueing a job."""
    job = await queue.enqueue(job_type="test", payload={"data": "value"}, priority=0)

    assert job.id.startswith("job_")
    assert job.job_type == "test"
    assert job.status == JobStatus.QUEUED
    assert job.payload == {"data": "value"}
    assert job.attempts == 0


@pytest.mark.asyncio
async def test_enqueue_with_idempotency(queue):
    """Test idempotency key prevents duplicates."""
    job1 = await queue.enqueue(
        job_type="test", payload={"data": "1"}, idempotency_key="unique_key"
    )

    job2 = await queue.enqueue(
        job_type="test", payload={"data": "2"}, idempotency_key="unique_key"
    )

    # Should return same job
    assert job1.id == job2.id
    assert job1.payload == job2.payload  # Original payload preserved


@pytest.mark.asyncio
async def test_get_job(queue):
    """Test retrieving a job."""
    created = await queue.enqueue(job_type="test", payload={})

    retrieved = await queue.get_job(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id


@pytest.mark.asyncio
async def test_get_nonexistent_job(queue):
    """Test getting non-existent job returns None."""
    job = await queue.get_job("nonexistent")

    assert job is None


@pytest.mark.asyncio
async def test_process_jobs(queue):
    """Test processing jobs from queue."""
    # Enqueue job
    await queue.enqueue(job_type="test", payload={"value": 1})

    # Process job
    async def worker():
        async for job in queue.process():
            assert job.status == JobStatus.PROCESSING
            assert job.attempts == 1
            await queue.complete(job.id)
            break  # Process one job then stop

    await asyncio.wait_for(worker(), timeout=1.0)


@pytest.mark.asyncio
async def test_complete_job(queue):
    """Test completing a job."""
    await queue.enqueue(job_type="test", payload={})

    # Process and complete
    async def worker():
        async for job in queue.process():
            completed = await queue.complete(job.id, result={"output": "success"})
            assert completed.status == JobStatus.COMPLETED
            assert completed.result == {"output": "success"}
            assert completed.completed_at is not None
            break

    await asyncio.wait_for(worker(), timeout=1.0)


@pytest.mark.asyncio
async def test_fail_job_with_retry(queue):
    """Test failing a job with retry."""
    job = await queue.enqueue(job_type="test", payload={}, max_retries=2)

    # Process and fail
    async def worker():
        async for job in queue.process():
            failed = await queue.fail(job.id, error="Test error", retry=True)
            assert failed.status == JobStatus.QUEUED  # Re-queued for retry
            assert failed.attempts == 1
            assert failed.error == "Test error"
            break

    await asyncio.wait_for(worker(), timeout=1.0)

    # Check it's back in queue
    retrieved = await queue.get_job(job.id)
    assert retrieved.status == JobStatus.QUEUED


@pytest.mark.asyncio
async def test_fail_job_max_retries(queue):
    """Test job fails after max retries."""
    await queue.enqueue(job_type="test", payload={}, max_retries=2)

    # Fail twice (first attempt + 1 retry)
    async def worker():
        async for job in queue.process():
            await queue.fail(job.id, error="First error", retry=True)
            break

    await asyncio.wait_for(worker(), timeout=1.0)

    # Try again (should still retry)
    async def worker2():
        async for job in queue.process():
            failed = await queue.fail(job.id, error="Second error", retry=True)
            assert (
                failed.status == JobStatus.FAILED
            )  # Permanently failed after 2 attempts
            assert failed.attempts == 2
            break

    await asyncio.wait_for(worker2(), timeout=1.0)


@pytest.mark.asyncio
async def test_cancel_job(queue):
    """Test cancelling a job."""
    job = await queue.enqueue(job_type="test", payload={})

    cancelled = await queue.cancel(job.id)

    assert cancelled.status == JobStatus.CANCELLED
    assert cancelled.completed_at is not None


@pytest.mark.asyncio
async def test_priority_ordering(queue):
    """Test jobs are processed by priority."""
    # Enqueue jobs with different priorities
    await queue.enqueue(job_type="low", payload={"p": 0}, priority=0)
    await queue.enqueue(job_type="high", payload={"p": 10}, priority=10)
    await queue.enqueue(job_type="medium", payload={"p": 5}, priority=5)

    # Process jobs
    processed_types = []

    async def worker():
        count = 0
        async for job in queue.process():
            processed_types.append(job.job_type)
            await queue.complete(job.id)
            count += 1
            if count == 3:
                break

    await asyncio.wait_for(worker(), timeout=2.0)

    # Should process high priority first
    assert processed_types[0] == "high"
    assert processed_types[1] == "medium"
    assert processed_types[2] == "low"


@pytest.mark.asyncio
async def test_get_stats(queue):
    """Test getting queue statistics."""
    # Enqueue jobs
    await queue.enqueue(job_type="test", payload={})
    await queue.enqueue(job_type="test", payload={})

    stats = await queue.get_stats()

    assert stats.total_jobs == 2
    assert stats.queued == 2
    assert stats.processing == 0
    assert stats.completed == 0
    assert stats.failed == 0


@pytest.mark.asyncio
async def test_health_check(queue):
    """Test health check."""
    health = await queue.health_check()

    assert health["healthy"] is True
    assert health["backend"] == "in-memory"
    assert "total_jobs" in health
