"""Example showing full extraction -> chunking -> embedding -> storage pipeline."""

import os
import tempfile
from pathlib import Path

# Check if all dependencies available
try:
    from gundy_ai.extractors import ParserRegistry, TXTParser
    from gundy_ai.chunker import TokenAwareChunker
    from gundy_ai.embeddings import OpenAIEmbeddingProvider

    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    print("Note: This example requires all gundy-ai libraries")
    print("Install with:")
    print("  cd ../extractors && poetry install")
    print("  cd ../chunker && poetry install")
    print("  cd ../embeddings && poetry install --extras openai")

from gundy_ai.vectorstore import ChromaDBAdapter


def full_rag_pipeline():
    """Demonstrate complete RAG pipeline: Extract → Chunk → Embed → Store."""

    print("=== Complete RAG Pipeline: Extract → Chunk → Embed → Store ===\n")

    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Create sample document
    document_text = """
    Vector databases are specialized databases optimized for storing and querying
    high-dimensional vector embeddings. They enable semantic search by finding
    vectors that are similar in meaning rather than exact text matches.

    Popular vector databases include ChromaDB, Pinecone, Weaviate, and FAISS.
    Each has different trade-offs in terms of performance, scalability, and features.

    ChromaDB is an open-source embedding database that provides a simple API
    for storing and querying embeddings. It's designed to be easy to use and
    works well for development and small to medium scale production workloads.

    FAISS (Facebook AI Similarity Search) is a library for efficient similarity
    search of dense vectors. It's highly optimized for performance but requires
    more setup and configuration.
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(document_text)
        doc_path = f.name

    vector_db_dir = tempfile.mkdtemp()

    try:
        # Step 1: Extract text from document
        print("Step 1: Extract Text")
        print("-" * 70)

        registry = ParserRegistry()
        registry.register(TXTParser())

        parser = registry.get_parser(".txt")
        extracted = parser.parse(doc_path)

        print(f"Parser: {parser.manifest.name}")
        print(f"Extracted: {len(extracted[0].text)} characters\n")

        # Step 2: Chunk the text
        print("Step 2: Chunk Text")
        print("-" * 70)

        chunker = TokenAwareChunker(max_tokens=100, overlap_tokens=20)
        chunks = chunker.chunk(extracted[0].text)

        print(f"Chunker: {chunker}")
        print(f"Chunks created: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):  # Show first 3
            print(
                f"  Chunk {i + 1}: {chunk.token_count} tokens, {chunk.char_count} chars"
            )

        print()

        # Step 3: Generate embeddings
        print("Step 3: Generate Embeddings")
        print("-" * 70)

        provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")

        # Embed all chunks
        chunk_texts = [chunk.text for chunk in chunks]
        embedding_result = provider.embed(chunk_texts)

        print(f"Provider: {provider}")
        print(f"Embeddings generated: {len(embedding_result.embeddings)}")
        print(f"Dimensions: {embedding_result.dimensions}")
        print(f"Total tokens: {embedding_result.total_tokens}")
        print(f"Cost: ${embedding_result.estimated_cost_usd:.6f}\n")

        # Step 4: Store in vector database
        print("Step 4: Store in Vector Database")
        print("-" * 70)

        store = ChromaDBAdapter(
            persist_directory=vector_db_dir, collection_name="documents"
        )

        # Prepare documents for storage
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"chunk_index": i, "token_count": chunk.token_count}
            for i, chunk in enumerate(chunks)
        ]

        store.upsert(
            ids=ids,
            embeddings=embedding_result.embeddings,
            metadatas=metadatas,
            texts=chunk_texts,
        )

        print(f"Store: {store}")
        print(f"Vectors stored: {store.count()}\n")

        # Step 5: Query the vector database
        print("Step 5: Query for Similar Content")
        print("-" * 70)

        # Generate embedding for query
        query = "What are popular vector databases?"
        query_result = provider.embed([query])
        query_embedding = query_result.embeddings[0]

        print(f'Query: "{query}"')
        print(f"Query embedding dimensions: {len(query_embedding)}\n")

        # Search for similar chunks
        results = store.query(query_embedding=query_embedding, top_k=3)

        print(f"Top {len(results)} results:")
        for i, result in enumerate(results):
            print(f"\n{i + 1}. {result.id} (score: {result.score:.3f})")
            print(f"   Tokens: {result.metadata.get('token_count')}")
            print(f'   Text: "{result.text[:100]}..."')

        # Summary
        print("\n" + "=" * 70)
        print("\nPipeline Summary:")
        print(f"  Input: 1 document ({len(document_text)} characters)")
        print(f"  Extracted: {len(extracted)} page(s)")
        print(f"  Chunked: {len(chunks)} text chunks")
        print(
            f"  Embedded: {len(embedding_result.embeddings)} vectors ({embedding_result.dimensions}D)"
        )
        print(f"  Stored: {store.count()} vectors in ChromaDB")
        print(f"  Total embedding cost: ${embedding_result.estimated_cost_usd:.6f}")
        print("\n✓ Complete RAG pipeline working!")
        print("\nNext steps:")
        print("  1. Add more documents to the vector store")
        print("  2. Build API endpoints for document upload and search")
        print("  3. Integrate with LLM for answer generation")
        print("  4. Deploy RAG chatbot")

    finally:
        Path(doc_path).unlink(missing_ok=True)
        import shutil

        shutil.rmtree(vector_db_dir, ignore_errors=True)


def storage_only_demo():
    """Demo with just vector storage (no extractors/chunker/embeddings)."""
    print("=== Vector Storage Demo ===\n")

    temp_dir = tempfile.mkdtemp()

    try:
        store = ChromaDBAdapter(persist_directory=temp_dir, collection_name="test")

        # Mock embeddings (normally from embedding service)
        store.upsert(
            ids=["doc1", "doc2"],
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            metadatas=[{"title": "Doc 1"}, {"title": "Doc 2"}],
        )

        results = store.query(query_embedding=[0.15, 0.25, 0.35], top_k=2)

        print(f"Stored {store.count()} vectors")
        print(f"Found {len(results)} similar vectors")

    finally:
        import shutil

        shutil.rmtree(temp_dir, ignore_errors=True)


def main():
    """Run appropriate demo based on what's available."""
    if DEPS_AVAILABLE:
        full_rag_pipeline()
    else:
        storage_only_demo()


if __name__ == "__main__":
    main()
