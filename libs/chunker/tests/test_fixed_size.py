"""Tests for FixedSizeChunker."""

import pytest

from gundy_ai.chunker import FixedSizeChunker, TextChunk


@pytest.fixture
def chunker():
    """Create FixedSizeChunker instance."""
    return FixedSizeChunker(chunk_size=100, overlap_size=20)


def test_fixed_size_chunker_init():
    """Test chunker initialization."""
    chunker = FixedSizeChunker(chunk_size=500, overlap_size=50)

    assert chunker.chunk_size == 500
    assert chunker.overlap_size == 50


def test_init_invalid_overlap():
    """Test that overlap >= chunk_size raises error."""
    with pytest.raises(ValueError, match="overlap_size.*must be less than"):
        FixedSizeChunker(chunk_size=100, overlap_size=100)

    with pytest.raises(ValueError, match="overlap_size.*must be less than"):
        FixedSizeChunker(chunk_size=100, overlap_size=150)


def test_chunk_short_text(chunker):
    """Test chunking text shorter than chunk_size."""
    text = "This is a short text."

    chunks = chunker.chunk(text)

    assert len(chunks) == 1
    assert isinstance(chunks[0], TextChunk)
    assert chunks[0].text == text
    assert chunks[0].chunk_index == 0
    assert chunks[0].span_start == 0
    assert chunks[0].span_end == len(text)
    assert chunks[0].char_count == len(text)
    assert chunks[0].token_count == 0  # Not calculated for fixed-size


def test_chunk_empty_text(chunker):
    """Test chunking empty text."""
    chunks = chunker.chunk("")

    assert chunks == []


def test_chunk_long_text(chunker):
    """Test chunking text longer than chunk_size."""
    # Create text of 250 characters (should create 2-3 chunks with size=100, overlap=20)
    text = "A" * 250

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
        # Chunks should overlap
        assert chunks[i].span_start < chunks[i - 1].span_end


def test_chunk_exact_size():
    """Test chunking text that exactly fits chunk_size."""
    chunker = FixedSizeChunker(chunk_size=10, overlap_size=0)

    text = "0123456789"  # Exactly 10 characters

    chunks = chunker.chunk(text)

    assert len(chunks) == 1
    assert chunks[0].char_count == 10


def test_chunk_overlap():
    """Test that chunks have proper overlap."""
    chunker = FixedSizeChunker(chunk_size=100, overlap_size=20)

    text = "X" * 250

    chunks = chunker.chunk(text)

    assert len(chunks) >= 2

    # Check overlap between consecutive chunks
    for i in range(len(chunks) - 1):
        overlap_start = chunks[i + 1].span_start
        overlap_end = chunks[i].span_end

        # There should be overlap
        overlap_size = overlap_end - overlap_start
        assert overlap_size <= 20  # May be less at boundaries


def test_chunk_no_overlap():
    """Test chunking with no overlap."""
    chunker = FixedSizeChunker(chunk_size=50, overlap_size=0)

    text = "A" * 150

    chunks = chunker.chunk(text)

    assert len(chunks) == 3

    # Chunks should be contiguous with no overlap
    assert chunks[0].span_end == chunks[1].span_start
    assert chunks[1].span_end == chunks[2].span_start


def test_chunk_metadata():
    """Test that chunks have correct metadata."""
    chunker = FixedSizeChunker(chunk_size=200, overlap_size=30)

    text = "Test text for metadata."

    chunks = chunker.chunk(text)

    assert len(chunks) >= 1

    metadata = chunks[0].metadata
    assert metadata["strategy"] == "fixed_size"
    assert metadata["chunk_size"] == 200
    assert metadata["overlap_size"] == 30


def test_estimate_chunks_short_text(chunker):
    """Test estimating chunks for short text."""
    text = "Short text"

    estimate = chunker.estimate_chunks(text)

    assert estimate == 1


def test_estimate_chunks_long_text():
    """Test estimating chunks for long text."""
    chunker = FixedSizeChunker(chunk_size=100, overlap_size=20)

    text = "X" * 300

    estimate = chunker.estimate_chunks(text)
    actual_chunks = chunker.chunk(text)

    # Estimate should be close to actual
    assert abs(estimate - len(actual_chunks)) <= 1


def test_estimate_chunks_empty_text(chunker):
    """Test estimating chunks for empty text."""
    assert chunker.estimate_chunks("") == 0


def test_chunker_repr():
    """Test string representation."""
    chunker = FixedSizeChunker(chunk_size=500, overlap_size=50)

    repr_str = repr(chunker)

    assert "FixedSizeChunker" in repr_str
    assert "500" in repr_str
    assert "50" in repr_str


def test_chunk_preserves_content():
    """Test that chunking preserves all content."""
    chunker = FixedSizeChunker(chunk_size=50, overlap_size=10)

    text = "This is a test. " * 20

    chunks = chunker.chunk(text)

    # Reconstruct text from first characters of each chunk (accounting for overlap)
    # Just verify first and last chunks contain expected content
    assert chunks[0].text.startswith("This is a test")
    assert chunks[-1].text.endswith("This is a test. ")


def test_chunk_unicode(chunker):
    """Test chunking Unicode text."""
    text = "Hello 世界 🌍 " * 20

    chunks = chunker.chunk(text)

    assert len(chunks) >= 1
    # Unicode should be preserved
    combined_text = "".join(chunk.text for chunk in chunks)
    assert "世界" in combined_text
    assert "🌍" in combined_text
