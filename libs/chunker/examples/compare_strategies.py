"""Compare different chunking strategies."""

from gundy_ai.chunker import FixedSizeChunker, TokenAwareChunker


def main():
    """Compare token-aware vs fixed-size chunking."""

    print("=== Chunking Strategy Comparison ===\n")

    # Sample text
    text = """
    Artificial intelligence and machine learning have revolutionized how we process
    and understand text. Modern language models can understand context, generate
    coherent responses, and even help with complex reasoning tasks. However, these
    models have token limits that we must respect. That's where intelligent chunking
    comes in - it allows us to split large documents into manageable pieces while
    maintaining semantic coherence and context through overlapping regions.
    """.strip()

    print(f"Input text: {len(text)} characters\n")
    print("=" * 70)

    # Strategy 1: Token-Aware
    print("\n1. TOKEN-AWARE STRATEGY")
    print("-" * 70)

    token_chunker = TokenAwareChunker(max_tokens=50, overlap_tokens=10)
    token_chunks = token_chunker.chunk(text)

    print(f"Chunker: {token_chunker}")
    print(f"Chunks created: {len(token_chunks)}")
    print(f"Estimated: {token_chunker.estimate_chunks(text)}\n")

    for i, chunk in enumerate(token_chunks):
        print(f"  Chunk {i + 1}: {chunk.token_count} tokens, {chunk.char_count} chars")
        print(f"    {chunk.text[:50]}...")

    # Strategy 2: Fixed-Size
    print("\n2. FIXED-SIZE STRATEGY")
    print("-" * 70)

    fixed_chunker = FixedSizeChunker(chunk_size=150, overlap_size=30)
    fixed_chunks = fixed_chunker.chunk(text)

    print(f"Chunker: {fixed_chunker}")
    print(f"Chunks created: {len(fixed_chunks)}")
    print(f"Estimated: {fixed_chunker.estimate_chunks(text)}\n")

    for i, chunk in enumerate(fixed_chunks):
        print(f"  Chunk {i + 1}: {chunk.char_count} chars (tokens not counted)")
        print(f"    {chunk.text[:50]}...")

    # Comparison
    print("\n" + "=" * 70)
    print("\nCOMPARISON:")
    print(f"  Token-Aware: {len(token_chunks)} chunks")
    print(f"  Fixed-Size:  {len(fixed_chunks)} chunks")
    print("\nWhen to use each:")
    print("  - Token-Aware: When sending to LLMs with strict token limits")
    print("  - Fixed-Size:  For simpler cases or when tokens don't matter")


if __name__ == "__main__":
    main()
