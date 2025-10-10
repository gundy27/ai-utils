"""Example showing full extraction -> chunking -> embedding pipeline."""

import os
import tempfile
from pathlib import Path

# Check if dependencies available
try:
    from gundy_ai.extractors import ParserRegistry, TXTParser
    from gundy_ai.chunker import TokenAwareChunker

    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    print("Note: This example requires gundy-ai-extractors and gundy-ai-chunker")
    print("Install with:")
    print("  cd ../extractors && poetry install")
    print("  cd ../chunker && poetry install")

from gundy_ai.embeddings import OpenAIEmbeddingProvider


def full_pipeline_demo():
    """Demonstrate complete document processing pipeline."""

    print("=== Full RAG Pipeline: Extract → Chunk → Embed ===\n")

    # Check API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Create sample document
    document_text = """
    Retrieval-Augmented Generation (RAG) is a powerful technique for building
    AI applications. It combines the power of large language models with
    external knowledge sources.

    The RAG process involves three main steps:
    1. Document extraction - converting files to text
    2. Text chunking - splitting into manageable pieces
    3. Embedding generation - converting text to vectors

    These vectors are then stored in a vector database for semantic search.
    When a user asks a question, we:
    - Convert the question to an embedding
    - Find similar document chunks
    - Send relevant chunks to the LLM for answer generation

    This approach provides several benefits:
    - Up-to-date information (not limited by training data)
    - Source attribution (cite specific documents)
    - Domain-specific knowledge (use your own documents)
    - Reduced hallucinations (grounded in real sources)
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(document_text)
        temp_path = f.name

    try:
        # Step 1: Extract text from document
        print("Step 1: Extract Text")
        print("-" * 70)

        registry = ParserRegistry()
        registry.register(TXTParser())

        parser = registry.get_parser(".txt")
        extracted = parser.parse(temp_path)

        print(f"Parser: {parser.manifest.name}")
        print(f"Extracted: {len(extracted[0].text)} characters\n")

        # Step 2: Chunk the text
        print("Step 2: Chunk Text")
        print("-" * 70)

        chunker = TokenAwareChunker(max_tokens=100, overlap_tokens=20)
        chunks = chunker.chunk(extracted[0].text)

        print(f"Chunker: {chunker}")
        print(f"Chunks created: {len(chunks)}")
        for i, chunk in enumerate(chunks):
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
        result = provider.embed(chunk_texts)

        print(f"Provider: {provider}")
        print(f"Embeddings generated: {len(result.embeddings)}")
        print(f"Dimensions: {result.dimensions}")
        print(f"Total tokens: {result.total_tokens}")
        print(f"Latency: {result.latency_ms:.1f}ms")
        print(f"Cost: ${result.estimated_cost_usd:.6f}\n")

        # Summary
        print("=" * 70)
        print("\nPipeline Summary:")
        print(f"  Input: 1 document ({len(document_text)} characters)")
        print(f"  Extracted: {len(extracted)} chunks")
        print(f"  Chunked: {len(chunks)} text chunks")
        print(f"  Embedded: {len(result.embeddings)} vectors ({result.dimensions}D)")
        print(f"  Total cost: ${result.estimated_cost_usd:.6f}")
        print("\n✓ Ready for vector database storage!")
        print("\nNext steps:")
        print("  1. Store embeddings in vector database (ChromaDB, FAISS, etc.)")
        print("  2. Enable semantic search over documents")
        print("  3. Build RAG chatbot for Q&A")

    finally:
        Path(temp_path).unlink(missing_ok=True)


def chunker_only_demo():
    """Demo with just embeddings (no extractors/chunker)."""
    print("=== Embeddings-Only Demo ===\n")

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")

    texts = [
        "First document about AI",
        "Second document about machine learning",
        "Third document about embeddings",
    ]

    result = provider.embed(texts)

    print(f"Embedded {len(texts)} texts")
    print(f"Dimensions: {result.dimensions}")
    print(f"Cost: ${result.estimated_cost_usd:.6f}")


def main():
    """Run appropriate demo based on what's available."""
    if DEPS_AVAILABLE:
        full_pipeline_demo()
    else:
        chunker_only_demo()


if __name__ == "__main__":
    main()
