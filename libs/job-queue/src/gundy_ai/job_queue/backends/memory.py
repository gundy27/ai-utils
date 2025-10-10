"""In-memory job queue implementation."""

import asyncio
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional

import structlog

from ..audit import JobEventType, emit_job_event
from ..base import BaseJobQueue
from ..models import Job, JobStats, JobStatus

logger = structlog.get_logger(__name__)


class InMemoryQueue(BaseJobQueue):
    """In-memory job queue for development and testing.

    Stores jobs in memory with priority queue ordering.
    Not suitable for production (no persistence across restarts).

    Example:
        queue = InMemoryQueue()

        job = await queue.enqueue(
            job_type="document_ingest",
            payload={"file": "doc.pdf"},
            idempotency_key="doc_123"
        )

        async for job in queue.process():
            result = await process_job(job)
            await queue.complete(job.id, result=result)
    """

    def __init__(self):
        """Initialize in-memory queue."""
        self._jobs: Dict[str, Job] = {}
        self._queue: deque[str] = deque()  # Job IDs in queue
        self._idempotency_map: Dict[str, str] = {}  # key -> job_id
        self._lock = asyncio.Lock()

        logger.info("inmemory_queue_initialized")

    async def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        priority: int = 0,
        max_retries: int = 3,
    ) -> Job:
        """Enqueue a new job."""
        async with self._lock:
            # Check idempotency
            if idempotency_key and idempotency_key in self._idempotency_map:
                existing_job_id = self._idempotency_map[idempotency_key]
                existing_job = self._jobs[existing_job_id]

                logger.info(
                    "job_deduplicated",
                    job_id=existing_job_id,
                    idempotency_key=idempotency_key,
                )

                return existing_job

            # Create new job
            job_id = f"job_{uuid.uuid4().hex[:16]}"

            job = Job(
                id=job_id,
                job_type=job_type,
                status=JobStatus.QUEUED,
                payload=payload,
                idempotency_key=idempotency_key,
                priority=priority,
                max_retries=max_retries,
            )

            self._jobs[job_id] = job

            # Add to queue (insert by priority)
            if priority > 0:
                # Insert in priority order (simple linear search for now)
                inserted = False
                for i, existing_id in enumerate(self._queue):
                    if self._jobs[existing_id].priority < priority:
                        self._queue.insert(i, job_id)
                        inserted = True
                        break
                if not inserted:
                    self._queue.append(job_id)
            else:
                self._queue.append(job_id)

            # Track idempotency
            if idempotency_key:
                self._idempotency_map[idempotency_key] = job_id

            emit_job_event(
                event_type=JobEventType.JOB_QUEUED,
                job_id=job_id,
                job_type=job_type,
                status=JobStatus.QUEUED.value,
                outcome="success",
                idempotency_key=idempotency_key,
                metadata={"priority": priority},
            )

            logger.info(
                "job_enqueued",
                job_id=job_id,
                job_type=job_type,
                priority=priority,
                idempotency_key=idempotency_key,
            )

            return job

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    async def process(self) -> AsyncIterator[Job]:
        """Process jobs from queue.

        Yields jobs and marks them as PROCESSING.
        """
        while True:
            async with self._lock:
                if not self._queue:
                    # No jobs available, wait a bit
                    await asyncio.sleep(0.1)
                    continue

                # Get next job
                job_id = self._queue.popleft()
                job = self._jobs.get(job_id)

                if not job:
                    continue

                # Mark as processing
                job.status = JobStatus.PROCESSING
                job.started_at = datetime.now(timezone.utc)
                job.attempts += 1

                emit_job_event(
                    event_type=JobEventType.JOB_STARTED,
                    job_id=job.id,
                    job_type=job.job_type,
                    status=JobStatus.PROCESSING.value,
                    outcome="success",
                    attempts=job.attempts,
                )

                logger.info(
                    "job_started",
                    job_id=job.id,
                    job_type=job.job_type,
                    attempt=job.attempts,
                )

            yield job

    async def complete(
        self, job_id: str, result: Optional[Dict[str, Any]] = None
    ) -> Job:
        """Mark job as completed."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            if job.status != JobStatus.PROCESSING:
                raise ValueError(f"Job not in processing state: {job.status}")

            processing_time_ms = None
            if job.started_at:
                processing_time_ms = (
                    datetime.now(timezone.utc) - job.started_at
                ).total_seconds() * 1000

            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.result = result

            emit_job_event(
                event_type=JobEventType.JOB_COMPLETED,
                job_id=job.id,
                job_type=job.job_type,
                status=JobStatus.COMPLETED.value,
                outcome="success",
                attempts=job.attempts,
                processing_time_ms=processing_time_ms,
            )

            logger.info(
                "job_completed",
                job_id=job.id,
                job_type=job.job_type,
                attempts=job.attempts,
                processing_time_ms=processing_time_ms,
            )

            return job

    async def fail(self, job_id: str, error: str, retry: bool = True) -> Job:
        """Mark job as failed."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            job.error = error

            # Determine if we should retry
            should_retry = retry and job.attempts < job.max_retries

            if should_retry:
                # Re-queue for retry
                job.status = JobStatus.QUEUED
                self._queue.append(job_id)

                emit_job_event(
                    event_type=JobEventType.JOB_RETRY,
                    job_id=job.id,
                    job_type=job.job_type,
                    status=JobStatus.QUEUED.value,
                    outcome="retry",
                    attempts=job.attempts,
                    error_message=error,
                    metadata={"max_retries": job.max_retries},
                )

                logger.warning(
                    "job_retry",
                    job_id=job.id,
                    job_type=job.job_type,
                    attempt=job.attempts,
                    max_retries=job.max_retries,
                    error=error,
                )
            else:
                # Mark as failed
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now(timezone.utc)

                emit_job_event(
                    event_type=JobEventType.JOB_FAILED,
                    job_id=job.id,
                    job_type=job.job_type,
                    status=JobStatus.FAILED.value,
                    outcome="failure",
                    attempts=job.attempts,
                    error_message=error,
                )

                logger.error(
                    "job_failed",
                    job_id=job.id,
                    job_type=job.job_type,
                    attempts=job.attempts,
                    error=error,
                )

            return job

    async def cancel(self, job_id: str) -> Job:
        """Cancel a job."""
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ValueError(f"Job not found: {job_id}")

            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now(timezone.utc)

            # Remove from queue if present
            if job_id in self._queue:
                self._queue.remove(job_id)

            emit_job_event(
                event_type=JobEventType.JOB_CANCELLED,
                job_id=job.id,
                job_type=job.job_type,
                status=JobStatus.CANCELLED.value,
                outcome="success",
            )

            logger.info("job_cancelled", job_id=job.id)

            return job

    async def get_stats(self) -> JobStats:
        """Get queue statistics."""
        async with self._lock:
            total = len(self._jobs)
            queued = sum(1 for j in self._jobs.values() if j.status == JobStatus.QUEUED)
            processing = sum(
                1 for j in self._jobs.values() if j.status == JobStatus.PROCESSING
            )
            completed = sum(
                1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED
            )
            failed = sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)

            return JobStats(
                total_jobs=total,
                queued=queued,
                processing=processing,
                completed=completed,
                failed=failed,
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check queue health."""
        stats = await self.get_stats()

        return {
            "healthy": True,
            "backend": "in-memory",
            "total_jobs": stats.total_jobs,
            "queued": stats.queued,
            "processing": stats.processing,
        }
