"""Tests for BaseChunker interface."""

from typing import List

from gundy_ai.chunker import BaseChunker, TextChunk


class MockChunker(BaseChunker):
    """Mock chunker for testing interface."""

    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        return [
            TextChunk(
                chunk_id="mock_0",
                text=text,
                token_count=1,
                char_count=len(text),
                chunk_index=0,
                span_start=0,
                span_end=len(text),
            )
        ]

    def estimate_chunks(self, text: str) -> int:
        return 1


def test_base_chunker_interface():
    """Test that BaseChunker interface can be implemented."""
    chunker = MockChunker()

    assert hasattr(chunker, "chunk")
    assert hasattr(chunker, "estimate_chunks")


def test_base_chunker_chunk():
    """Test that chunk method returns TextChunk objects."""
    chunker = MockChunker()
    chunks = chunker.chunk("test text")

    assert len(chunks) == 1
    assert isinstance(chunks[0], TextChunk)
    assert chunks[0].text == "test text"


def test_base_chunker_estimate():
    """Test estimate_chunks method."""
    chunker = MockChunker()

    estimate = chunker.estimate_chunks("test")

    assert estimate == 1


def test_chunker_repr():
    """Test string representation."""
    chunker = MockChunker()

    repr_str = repr(chunker)

    assert "MockChunker" in repr_str
