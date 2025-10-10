"""Basic usage example for gundy-ai-vectorstore."""

import tempfile

from gundy_ai.vectorstore import ChromaDBAdapter


def main():
    """Demonstrate basic vector store usage."""

    print("=== Gundy AI Vector Store - Basic Usage ===\n")

    # Create temporary database directory
    temp_dir = tempfile.mkdtemp()

    try:
        # Create vector store
        store = ChromaDBAdapter(persist_directory=temp_dir, collection_name="documents")

        print(f"Store: {store}")
        print(f"Collection: {store.collection_name}\n")

        # Health check
        print("Running health check...")
        health = store.health_check()

        if health["healthy"]:
            print(
                f"✓ Store healthy (count: {health['count']}, latency: {health['latency_ms']:.1f}ms)\n"
            )
        else:
            print(f"✗ Store unhealthy: {health.get('error')}\n")
            return

        # Sample documents with embeddings (normally from embedding service)
        documents = [
            {
                "id": "doc1",
                "text": "Machine learning is transforming AI",
                "embedding": [0.1, 0.2, 0.3, 0.4],
                "metadata": {"category": "AI", "page": 1},
            },
            {
                "id": "doc2",
                "text": "Deep learning uses neural networks",
                "embedding": [0.2, 0.3, 0.4, 0.5],
                "metadata": {"category": "AI", "page": 2},
            },
            {
                "id": "doc3",
                "text": "Python is great for data science",
                "embedding": [0.5, 0.6, 0.7, 0.8],
                "metadata": {"category": "Programming", "page": 1},
            },
        ]

        # Upsert documents
        print(f"Upserting {len(documents)} documents...")
        store.upsert(
            ids=[doc["id"] for doc in documents],
            embeddings=[doc["embedding"] for doc in documents],
            metadatas=[doc["metadata"] for doc in documents],
            texts=[doc["text"] for doc in documents],
        )

        print(f"✓ Upserted {len(documents)} documents")
        print(f"Total count: {store.count()}\n")

        # Query for similar documents
        print("Querying for documents similar to [0.15, 0.25, 0.35, 0.45]...")
        query_embedding = [0.15, 0.25, 0.35, 0.45]

        results = store.query(query_embedding=query_embedding, top_k=2)

        print(f"\nTop {len(results)} results:")
        for i, result in enumerate(results):
            print(f"  {i + 1}. {result.id} (score: {result.score:.3f})")
            print(f'     Text: "{result.text}"')
            print(f"     Metadata: {result.metadata}")

        # Query with metadata filter
        print("\nQuerying with filter (category='AI')...")
        filtered_results = store.query(
            query_embedding=query_embedding, top_k=5, filter={"category": "AI"}
        )

        print(f"Found {len(filtered_results)} AI documents:")
        for result in filtered_results:
            print(f"  - {result.id}: {result.metadata['category']}")

        # Delete a document
        print("\nDeleting doc2...")
        deleted = store.delete(["doc2"])
        print(f"✓ Deleted {deleted} document(s)")
        print(f"Remaining count: {store.count()}\n")

        print("✓ Vector store operations completed successfully!")

    finally:
        # Cleanup
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
