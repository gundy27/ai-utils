"""Example RAG document processing worker with job queue."""

import asyncio
import os
from pathlib import Path

# Check dependencies
try:
    from gundy_ai.extractors import ParserRegistry, TXTParser
    from gundy_ai.chunker import TokenAwareChunker
    from gundy_ai.embeddings import OpenAIEmbeddingProvider
    from gundy_ai.vectorstore import ChromaDBAdapter
    from gundy_ai.metadata_store import MetadataStore

    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    print("Note: This example requires all gundy-ai libraries")

from gundy_ai.job_queue import InMemoryQueue


async def process_document_job(
    payload, parser_registry, chunker, embeddings, vectorstore, metadata_store
):
    """Process a document ingestion job.

    Args:
        payload: Job payload with file info
        parser_registry: Parser registry
        chunker: Text chunker
        embeddings: Embedding provider
        vectorstore: Vector store
        metadata_store: Metadata store

    Returns:
        Processing result
    """
    file_path = payload["file_path"]
    user_id = payload.get("user_id", "system")

    # Get file extension and parser
    file_ext = Path(file_path).suffix
    parser = parser_registry.get_parser(file_ext)

    # Extract text
    extracted = parser.parse(file_path)

    # Chunk text
    all_chunks = []
    for page in extracted:
        chunks = chunker.chunk(page.text)
        all_chunks.extend(chunks)

    # Generate embeddings
    chunk_texts = [chunk.text for chunk in all_chunks]
    embedding_result = embeddings.embed(chunk_texts)

    # Generate document ID
    document_id = f"doc_{Path(file_path).stem}"

    # Store in vectorstore
    chunk_ids = [f"{document_id}_chunk_{i}" for i in range(len(all_chunks))]
    vectorstore.upsert(
        ids=chunk_ids,
        embeddings=embedding_result.embeddings,
        metadatas=[{"document_id": document_id} for _ in all_chunks],
        texts=chunk_texts,
    )

    # Track in metadata store
    document = await metadata_store.create_document(
        name=Path(file_path).name,
        user_id=user_id,
        chunks=chunk_ids,
        status="completed",
        file_type=file_ext,
    )

    return {
        "document_id": document.id,
        "chunks_created": len(all_chunks),
        "total_tokens": embedding_result.total_tokens,
        "cost_usd": embedding_result.estimated_cost_usd,
    }


async def worker(queue, components):
    """Job worker that processes document ingestion jobs.

    Args:
        queue: Job queue
        components: Dict with all RAG components
    """
    print("Worker started, waiting for jobs...\n")

    async for job in queue.process():
        print(f"Processing job: {job.id}")
        print(f"  Type: {job.job_type}")
        print(f"  Attempt: {job.attempts}/{job.max_retries}")

        try:
            if job.job_type == "document_ingest":
                result = await process_document_job(job.payload, **components)
                await queue.complete(job.id, result=result)

                print("  ✓ Completed:")
                print(f"    Document: {result['document_id']}")
                print(f"    Chunks: {result['chunks_created']}")
                print(f"    Cost: ${result['cost_usd']:.6f}\n")
            else:
                await queue.fail(job.id, error=f"Unknown job type: {job.job_type}")

        except Exception as e:
            print(f"  ✗ Failed: {e}\n")
            await queue.fail(job.id, error=str(e), retry=True)


async def main():
    """Demonstrate RAG worker with job queue."""

    if not DEPS_AVAILABLE:
        print("This example requires all gundy-ai libraries installed")
        return

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    print("=== RAG Document Processing Worker ===\n")

    # Initialize queue
    queue = InMemoryQueue()

    # Initialize RAG components
    print("Initializing components...")
    parser_registry = ParserRegistry()
    parser_registry.register(TXTParser())

    chunker = TokenAwareChunker(max_tokens=512, overlap_tokens=50)
    embeddings = OpenAIEmbeddingProvider()
    vectorstore = ChromaDBAdapter(persist_directory="./temp_vector_db")
    metadata_store = MetadataStore("sqlite+aiosqlite:///./temp_metadata.db")
    await metadata_store.initialize()

    components = {
        "parser_registry": parser_registry,
        "chunker": chunker,
        "embeddings": embeddings,
        "vectorstore": vectorstore,
        "metadata_store": metadata_store,
    }

    print("✓ Components ready\n")

    # Create sample document
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(
            "Job queues enable async document processing. "
            "They provide retry logic and idempotency guarantees."
        )
        temp_file = f.name

    try:
        # Enqueue job
        print("Enqueueing document processing job...")
        job = await queue.enqueue(
            job_type="document_ingest",
            payload={"file_path": temp_file, "user_id": "demo_user"},
            idempotency_key=f"doc_{Path(temp_file).stem}",
        )

        print(f"Job enqueued: {job.id}\n")

        # Run worker (will process one job then stop)
        worker_task = asyncio.create_task(worker(queue, components))

        # Wait a bit for processing
        await asyncio.sleep(2)

        # Cancel worker
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass

        # Show final stats
        print("Final Statistics:")
        stats = await queue.get_stats()
        print(f"  Total jobs: {stats.total_jobs}")
        print(f"  Completed: {stats.completed}")
        print(f"  Failed: {stats.failed}\n")

        print("✓ Worker demo complete!")

    finally:
        Path(temp_file).unlink(missing_ok=True)
        Path("./temp_metadata.db").unlink(missing_ok=True)
        import shutil

        shutil.rmtree("./temp_vector_db", ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
