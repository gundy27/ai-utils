# Gundy AI Job Queue

Background job processing for RAG applications with support for multiple backends. Provides idempotent job execution with retry logic and comprehensive lifecycle tracking.

## Features

- **Multiple Backends**: In-memory (dev) and Redis (production - future)
- **Idempotent Jobs**: Prevent duplicate processing with idempotency keys
- **Retry Logic**: Automatic retries with configurable max attempts
- **Priority Queue**: Process high-priority jobs first
- **Job Lifecycle**: Track queued → processing → completed/failed
- **Audit Logging**: Track all job events with structured logging
- **Type-Safe**: Full Pydantic models
- **Async Support**: Fully async-compatible
- **Worker Pattern**: Async iteration for job processing

## Installation

```bash
# Base installation with in-memory backend
poetry add gundy-ai-job-queue

# With Redis backend (coming soon)
poetry add gundy-ai-job-queue[redis]
```

## Quick Start

```python
from gundy_ai.job_queue import InMemoryQueue

# Create queue
queue = InMemoryQueue()

# Enqueue job
job = await queue.enqueue(
    job_type="document_ingest",
    payload={"file_path": "/path/to/doc.pdf"},
    idempotency_key="doc_123",
    priority=10  # Higher = processed first
)

# Process jobs (in worker)
async for job in queue.process():
    try:
        # Do work
        result = await process_document(job.payload)
        await queue.complete(job.id, result=result)
    except Exception as e:
        await queue.fail(job.id, error=str(e), retry=True)
```

## Supported Backends

### InMemoryQueue ✅

Simple in-memory queue for development and testing.

**Features**:

- Priority queue ordering
- Idempotency support
- Automatic retries
- Thread-safe with async locks

**Limitations**:

- Not persistent (lost on restart)
- Single-process only

### Redis Queue 🔜

Coming soon for production use:

- Persistent across restarts
- Multi-worker support
- Distributed processing

## RAG Integration

Complete example with document processing:

```python
from gundy_ai.job_queue import InMemoryQueue
from gundy_ai.extractors import ParserRegistry, PDFParser
from gundy_ai.chunker import TokenAwareChunker
from gundy_ai.embeddings import OpenAIEmbeddingProvider
from gundy_ai.vectorstore import ChromaDBAdapter
from gundy_ai.metadata_store import MetadataStore

# Initialize components
queue = InMemoryQueue()
parser_registry = ParserRegistry()
parser_registry.register(PDFParser())
chunker = TokenAwareChunker(max_tokens=512)
embeddings = OpenAIEmbeddingProvider()
vectorstore = ChromaDBAdapter(persist_directory="./vector_db")
metadata_store = MetadataStore("sqlite+aiosqlite:///./metadata.db")
await metadata_store.initialize()

# Enqueue document processing job
job = await queue.enqueue(
    job_type="document_ingest",
    payload={
        "file_path": "document.pdf",
        "user_id": "user123"
    },
    idempotency_key="doc_abc"
)

# Worker to process jobs
async def worker():
    async for job in queue.process():
        try:
            # Extract, chunk, embed, store
            file_path = job.payload["file_path"]
            extracted = parser_registry.get_parser(".pdf").parse(file_path)

            all_chunks = []
            for page in extracted:
                chunks = chunker.chunk(page.text)
                all_chunks.extend(chunks)

            chunk_texts = [c.text for c in all_chunks]
            embedding_result = embeddings.embed(chunk_texts)

            chunk_ids = [f"doc_abc_chunk_{i}" for i in range(len(all_chunks))]
            vectorstore.upsert(
                ids=chunk_ids,
                embeddings=embedding_result.embeddings,
                texts=chunk_texts
            )

            # Track in metadata store
            await metadata_store.create_document(
                name=file_path,
                user_id=job.payload["user_id"],
                chunks=chunk_ids,
                status="completed"
            )

            # Complete job
            await queue.complete(job.id, result={
                "chunks": len(all_chunks),
                "cost": embedding_result.estimated_cost_usd
            })

        except Exception as e:
            await queue.fail(job.id, error=str(e), retry=True)

# Run worker
await worker()
```

## API Reference

### InMemoryQueue

**Methods**:

**`enqueue(job_type, payload, idempotency_key=None, priority=0, max_retries=3)`**

Enqueue a new job. Returns existing job if idempotency_key matches.

**`process()`**

Async iterator that yields jobs ready for processing. Jobs are automatically marked as PROCESSING.

**`complete(job_id, result=None)`**

Mark job as completed with optional result data.

**`fail(job_id, error, retry=True)`**

Mark job as failed. Re-queues if retry=True and attempts < max_retries.

**`cancel(job_id)`**

Cancel a queued job.

**`get_job(job_id)`**

Retrieve job by ID.

**`get_stats()`**

Get queue statistics (total, queued, processing, completed, failed).

**`health_check()`**

Check queue health.

## Job Lifecycle

```
QUEUED → PROCESSING → COMPLETED
   ↓         ↓
   ↓      FAILED (retry?) → QUEUED (retry) → PROCESSING
   ↓                      ↘ FAILED (max retries)
CANCELLED
```

## Idempotency

Prevent duplicate job processing:

```python
# First enqueue
job1 = await queue.enqueue(
    job_type="ingest",
    payload={"file": "doc.pdf"},
    idempotency_key="doc_123"
)

# Duplicate enqueue (returns existing job)
job2 = await queue.enqueue(
    job_type="ingest",
    payload={"file": "different.pdf"},  # Different payload
    idempotency_key="doc_123"  # Same key
)

assert job1.id == job2.id  # Same job returned
assert job1.payload == job2.payload  # Original payload preserved
```

## Priority Queues

Higher priority jobs processed first:

```python
await queue.enqueue(job_type="low", payload={}, priority=0)
await queue.enqueue(job_type="high", payload={}, priority=10)
await queue.enqueue(job_type="medium", payload={}, priority=5)

# Processing order: high (10) → medium (5) → low (0)
```

## Retry Logic

Automatic retries for failed jobs:

```python
job = await queue.enqueue(
    job_type="test",
    payload={},
    max_retries=3  # Will retry up to 3 times
)

# In worker
async for job in queue.process():
    try:
        result = await risky_operation()
        await queue.complete(job.id, result=result)
    except Exception as e:
        # Will retry if attempts < max_retries
        await queue.fail(job.id, error=str(e), retry=True)
```

## Audit Logging

All job lifecycle events are logged:

- `job.queued` - Job added to queue
- `job.started` - Job processing started
- `job.completed` - Job completed successfully
- `job.failed` - Job failed (no more retries)
- `job.retry` - Job being retried
- `job.cancelled` - Job cancelled

Events include:

- Job ID and type
- Idempotency key
- Attempt count
- Processing time
- Error messages

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific tests
poetry run pytest tests/backends/test_memory.py -v
```

**Test Coverage**: 16 tests, 93% coverage

## Examples

See `examples/` directory:

- `basic_usage.py`: Simple job queue operations
- `rag_worker.py`: Complete document processing worker

## Worker Patterns

### Single Worker

```python
async def worker():
    async for job in queue.process():
        await process_job(job)
```

### Multiple Workers

```python
async def run_workers(num_workers=3):
    workers = [
        asyncio.create_task(worker(i))
        for i in range(num_workers)
    ]
    await asyncio.gather(*workers)
```

### Worker with Timeout

```python
async def worker_with_timeout():
    async for job in queue.process():
        try:
            result = await asyncio.wait_for(
                process_job(job),
                timeout=300  # 5 minutes
            )
            await queue.complete(job.id, result=result)
        except asyncio.TimeoutError:
            await queue.fail(job.id, error="Timeout", retry=True)
```

## Performance

In-memory queue performance:

- Enqueue: <1ms
- Process: ~0.1ms overhead per job
- Scales to thousands of jobs
- Single-process only

## Future: Redis Backend

Coming soon for production use:

```python
from gundy_ai.job_queue import RedisQueue

queue = RedisQueue(
    redis_url="redis://localhost:6379/0",
    queue_name="rag_jobs"
)

# Same API as InMemoryQueue
job = await queue.enqueue(...)
```

## Requirements

- Python >=3.11,<3.13
- pydantic >=2.5,<3.0
- structlog >=23.2,<25.0
- redis >=5.0,<6.0 (for Redis backend - future)

## License

See main ai-utils repository.

## Contributing

Follow the project guidelines in `.cursorrules` at repository root.
