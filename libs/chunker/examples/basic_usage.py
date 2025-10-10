"""Basic usage example for gundy-ai-chunker."""

from gundy_ai.chunker import TokenAwareChunker


def main():
    """Demonstrate basic chunker usage."""

    print("=== Gundy AI Chunker - Basic Usage ===\n")

    # Create a token-aware chunker
    chunker = TokenAwareChunker(max_tokens=50, overlap_tokens=10)

    print(f"Chunker: {chunker}\n")

    # Sample text
    text = """
    This is a sample document that demonstrates the token-aware chunking system.
    The chunker will split this text into multiple chunks while respecting token limits.
    Each chunk will have some overlap with the previous chunk to maintain context.
    This is important for RAG applications where context matters.
    """.strip()

    print(f"Input text ({len(text)} characters):")
    print(f"{text[:100]}...\n")

    # Estimate chunks
    estimated = chunker.estimate_chunks(text)
    print(f"Estimated chunks: {estimated}\n")

    # Chunk the text
    chunks = chunker.chunk(text)

    print(f"Actual chunks created: {len(chunks)}\n")

    # Display chunks
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i + 1}:")
        print(f"  ID: {chunk.chunk_id}")
        print(f"  Tokens: {chunk.token_count}")
        print(f"  Characters: {chunk.char_count}")
        print(f"  Span: {chunk.span_start}-{chunk.span_end}")
        print(f"  Preview: {chunk.text[:60]}...")
        print()

    # Summary
    total_tokens = sum(c.token_count for c in chunks)
    total_chars = sum(c.char_count for c in chunks)

    print("Summary:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Total tokens (with overlap): {total_tokens}")
    print(f"  Total characters (with overlap): {total_chars}")
    print(f"  Original text: {len(text)} characters")


if __name__ == "__main__":
    main()
