"""Example showing integration with gundy-ai-extractors."""

import tempfile
from pathlib import Path

# Check if extractors is available
try:
    from gundy_ai.extractors import ParserRegistry, TXTParser

    EXTRACTORS_AVAILABLE = True
except ImportError:
    EXTRACTORS_AVAILABLE = False
    print("Note: gundy-ai-extractors not installed. Install with:")
    print("  cd ../extractors && poetry install")
    print("\nRunning chunker-only demo instead...\n")

from gundy_ai.chunker import TokenAwareChunker


def demo_with_extractors():
    """Demonstrate full extraction + chunking pipeline."""
    print("=== Extraction + Chunking Pipeline ===\n")

    # Step 1: Extract text from document
    print("Step 1: Extract text from document")
    print("-" * 60)

    registry = ParserRegistry()
    registry.register(TXTParser())

    # Create sample document
    sample_text = """
    Machine learning is transforming document processing.
    
    Key technologies include:
    1. Natural language processing for understanding text
    2. Vector embeddings for semantic search
    3. Large language models for generation
    
    The future of document AI looks promising with advances in:
    - Multimodal understanding
    - Better context handling
    - More efficient architectures
    """.strip()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(sample_text)
        temp_path = f.name

    try:
        parser = registry.get_parser(".txt")
        extracted = parser.parse(temp_path)

        print(f"Parser: {parser.manifest.name}")
        print(f"Extracted chunks: {len(extracted)}")
        print(f"Total characters: {len(extracted[0].text)}\n")

        # Step 2: Chunk the extracted text
        print("Step 2: Chunk extracted text for LLM processing")
        print("-" * 60)

        chunker = TokenAwareChunker(max_tokens=50, overlap_tokens=10)
        chunks = chunker.chunk(extracted[0].text)

        print(f"Chunker: {chunker}")
        print(f"Chunks created: {len(chunks)}\n")

        # Display chunks
        for i, chunk in enumerate(chunks):
            print(f"Chunk {i + 1}:")
            print(f"  Tokens: {chunk.token_count}")
            print(f"  Preview: {chunk.text[:60]}...")

        print("\n✓ Pipeline complete: Document → Extract → Chunk → Ready for RAG")

    finally:
        Path(temp_path).unlink(missing_ok=True)


def demo_chunker_only():
    """Demonstrate chunker without extractors."""
    print("=== Chunker-Only Demo ===\n")

    text = """
    This is a sample text for chunking.
    The token-aware chunker will split it intelligently based on token limits.
    Each chunk will maintain context through overlapping tokens.
    """.strip()

    chunker = TokenAwareChunker(max_tokens=30, overlap_tokens=5)

    print(f"Chunker: {chunker}")
    print(f"Input: {len(text)} characters\n")

    chunks = chunker.chunk(text)

    print(f"Chunks created: {len(chunks)}\n")

    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}: {chunk.token_count} tokens")
        print(f"  {chunk.text}\n")


def main():
    """Run appropriate demo based on what's available."""
    if EXTRACTORS_AVAILABLE:
        demo_with_extractors()
    else:
        demo_chunker_only()


if __name__ == "__main__":
    main()
