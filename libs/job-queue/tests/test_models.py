"""Tests for job models."""

from gundy_ai.job_queue import Job, JobRequest, JobStats, JobStatus


def test_job_status_enum():
    """Test JobStatus enum values."""
    assert JobStatus.QUEUED == "queued"
    assert JobStatus.PROCESSING == "processing"
    assert JobStatus.COMPLETED == "completed"
    assert JobStatus.FAILED == "failed"


def test_job_request_creation():
    """Test creating a JobRequest."""
    req = JobRequest(
        job_type="document_ingest",
        payload={"file": "test.pdf"},
        idempotency_key="test_123",
        priority=5,
    )

    assert req.job_type == "document_ingest"
    assert req.payload == {"file": "test.pdf"}
    assert req.idempotency_key == "test_123"
    assert req.priority == 5


def test_job_creation():
    """Test creating a Job."""
    job = Job(
        id="job_123",
        job_type="test",
        status=JobStatus.QUEUED,
        payload={"data": "value"},
    )

    assert job.id == "job_123"
    assert job.status == JobStatus.QUEUED
    assert job.attempts == 0


def test_job_stats_creation():
    """Test creating JobStats."""
    stats = JobStats(total_jobs=100, queued=10, processing=5, completed=80, failed=5)

    assert stats.total_jobs == 100
    assert stats.queued == 10
    assert stats.completed == 80
