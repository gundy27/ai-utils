"""Base job queue interface."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, Optional

from .models import Job, JobStats


class BaseJobQueue(ABC):
    """Abstract base class for job queues.

    All job queue implementations must implement this interface.
    Supports async iteration for worker processing.

    Example:
        queue = InMemoryQueue()

        # Enqueue job
        job = await queue.enqueue(
            job_type="document_ingest",
            payload={"file": "doc.pdf"}
        )

        # Process jobs
        async for job in queue.process():
            result = do_work(job.payload)
            await queue.complete(job.id, result=result)
    """

    @abstractmethod
    async def enqueue(
        self,
        job_type: str,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        priority: int = 0,
        max_retries: int = 3,
    ) -> Job:
        """Enqueue a new job.

        Args:
            job_type: Type of job
            payload: Job data
            idempotency_key: Key to prevent duplicate jobs
            priority: Job priority (higher = first)
            max_retries: Maximum retry attempts

        Returns:
            Created Job object

        Raises:
            ValueError: If validation fails
        """
        pass

    @abstractmethod
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job object or None if not found
        """
        pass

    @abstractmethod
    async def process(self) -> AsyncIterator[Job]:
        """Process jobs from queue.

        Yields jobs in priority order (FIFO within priority).
        Updates job status to PROCESSING when yielded.

        Yields:
            Job objects ready for processing
        """
        pass

    @abstractmethod
    async def complete(
        self, job_id: str, result: Optional[Dict[str, Any]] = None
    ) -> Job:
        """Mark job as completed.

        Args:
            job_id: Job identifier
            result: Optional result data

        Returns:
            Updated Job object

        Raises:
            ValueError: If job not found or not in processing state
        """
        pass

    @abstractmethod
    async def fail(self, job_id: str, error: str, retry: bool = True) -> Job:
        """Mark job as failed.

        Args:
            job_id: Job identifier
            error: Error message
            retry: Whether to retry (if attempts < max_retries)

        Returns:
            Updated Job object
        """
        pass

    @abstractmethod
    async def cancel(self, job_id: str) -> Job:
        """Cancel a job.

        Args:
            job_id: Job identifier

        Returns:
            Updated Job object

        Raises:
            ValueError: If job not found
        """
        pass

    @abstractmethod
    async def get_stats(self) -> JobStats:
        """Get queue statistics.

        Returns:
            JobStats with queue metrics
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check if queue is healthy.

        Returns:
            Health status dictionary
        """
        pass

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}()"
