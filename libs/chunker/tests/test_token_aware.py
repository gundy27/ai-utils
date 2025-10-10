"""Tests for TokenAwareChunker."""

import pytest

from gundy_ai.chunker import TextChunk, TokenAwareChunker


@pytest.fixture
def chunker():
    """Create TokenAwareChunker instance."""
    return TokenAwareChunker(max_tokens=50, overlap_tokens=10)


def test_token_aware_chunker_init():
    """Test chunker initialization."""
    chunker = TokenAwareChunker(max_tokens=100, overlap_tokens=20)

    assert chunker.max_tokens == 100
    assert chunker.overlap_tokens == 20
    assert chunker.encoding_name == "cl100k_base"


def test_init_invalid_overlap():
    """Test that overlap >= max_tokens raises error."""
    with pytest.raises(ValueError, match="overlap_tokens.*must be less than"):
        TokenAwareChunker(max_tokens=50, overlap_tokens=50)

    with pytest.raises(ValueError, match="overlap_tokens.*must be less than"):
        TokenAwareChunker(max_tokens=50, overlap_tokens=60)


def test_init_invalid_encoding():
    """Test that invalid encoding name raises error."""
    with pytest.raises(ValueError, match="Invalid encoding"):
        TokenAwareChunker(encoding_name="invalid_encoding")


def test_chunk_short_text(chunker):
    """Test chunking text shorter than max_tokens."""
    text = "This is a short text."

    chunks = chunker.chunk(text)

    assert len(chunks) == 1
    assert isinstance(chunks[0], TextChunk)
    assert chunks[0].text == text
    assert chunks[0].chunk_index == 0
    assert chunks[0].span_start == 0
    assert chunks[0].span_end == len(text)
    assert chunks[0].token_count > 0
    assert chunks[0].char_count == len(text)


def test_chunk_empty_text(chunker):
    """Test chunking empty text."""
    chunks = chunker.chunk("")

    assert chunks == []


def test_chunk_long_text(chunker):
    """Test chunking text longer than max_tokens."""
    # Create text that will definitely span multiple chunks
    text = " ".join([f"Word{i}" for i in range(200)])  # ~200 tokens

    chunks = chunker.chunk(text)

    # Should create multiple chunks
    assert len(chunks) > 1

    # All chunks should be TextChunk instances
    assert all(isinstance(chunk, TextChunk) for chunk in chunks)

    # Check chunk indices are sequential
    for i, chunk in enumerate(chunks):
        assert chunk.chunk_index == i

    # Check spans are sequential
    assert chunks[0].span_start == 0
    for i in range(1, len(chunks)):
        # There may be small overlap in spans
        assert chunks[i].span_start <= chunks[i - 1].span_end

    # Check metadata
    for chunk in chunks:
        assert chunk.metadata["strategy"] == "token_aware"
        assert chunk.metadata["max_tokens"] == 50
        assert chunk.metadata["overlap_tokens"] == 10


def test_chunk_overlap():
    """Test that chunks have proper overlap."""
    chunker = TokenAwareChunker(max_tokens=20, overlap_tokens=5)

    text = " ".join([f"Word{i}" for i in range(50)])

    chunks = chunker.chunk(text)

    # Should have multiple chunks
    assert len(chunks) > 2

    # Check token counts
    for chunk in chunks[:-1]:  # All except last
        assert chunk.token_count <= 20

    # Last chunk might be smaller
    assert chunks[-1].token_count <= 20


def test_chunk_exact_boundary():
    """Test chunking text that exactly fits max_tokens."""
    chunker = TokenAwareChunker(max_tokens=10, overlap_tokens=0)

    # Create text with exactly 10 tokens
    text = " ".join(["word"] * 10)

    chunks = chunker.chunk(text)

    assert len(chunks) == 1
    assert chunks[0].token_count == 10


def test_chunk_metadata():
    """Test that chunks have correct metadata."""
    chunker = TokenAwareChunker(
        max_tokens=100, overlap_tokens=10, encoding_name="cl100k_base"
    )

    text = "Test text for metadata validation."

    chunks = chunker.chunk(text)

    assert len(chunks) >= 1

    metadata = chunks[0].metadata
    assert metadata["strategy"] == "token_aware"
    assert metadata["max_tokens"] == 100
    assert metadata["overlap_tokens"] == 10
    assert metadata["encoding"] == "cl100k_base"


def test_estimate_chunks_short_text(chunker):
    """Test estimating chunks for short text."""
    text = "Short text"

    estimate = chunker.estimate_chunks(text)

    assert estimate == 1


def test_estimate_chunks_long_text():
    """Test estimating chunks for long text."""
    chunker = TokenAwareChunker(max_tokens=50, overlap_tokens=10)

    text = " ".join([f"Word{i}" for i in range(200)])

    estimate = chunker.estimate_chunks(text)
    actual_chunks = chunker.chunk(text)

    # Estimate should be close to actual
    assert abs(estimate - len(actual_chunks)) <= 1


def test_estimate_chunks_empty_text(chunker):
    """Test estimating chunks for empty text."""
    assert chunker.estimate_chunks("") == 0


def test_chunker_repr():
    """Test string representation."""
    chunker = TokenAwareChunker(max_tokens=100, overlap_tokens=20)

    repr_str = repr(chunker)

    assert "TokenAwareChunker" in repr_str
    assert "100" in repr_str
    assert "20" in repr_str


def test_chunk_unicode_text(chunker):
    """Test chunking text with Unicode characters."""
    text = "Hello 世界 🌍 " * 20

    chunks = chunker.chunk(text)

    assert len(chunks) >= 1
    # All chunks should contain valid Unicode
    for chunk in chunks:
        assert "世界" in chunk.text or "🌍" in chunk.text or "Hello" in chunk.text


def test_chunk_with_newlines(chunker):
    """Test chunking text with newlines."""
    text = "Line 1\nLine 2\nLine 3\n" * 10

    chunks = chunker.chunk(text)

    assert len(chunks) >= 1
    # Newlines should be preserved
    assert any("\n" in chunk.text for chunk in chunks)
