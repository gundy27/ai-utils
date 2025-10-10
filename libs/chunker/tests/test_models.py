"""Tests for data models."""

from gundy_ai.chunker import ChunkerConfig, TextChunk


def test_text_chunk_creation():
    """Test creating a TextChunk."""
    chunk = TextChunk(
        chunk_id="test_0",
        text="Sample text",
        token_count=2,
        char_count=11,
        chunk_index=0,
        span_start=0,
        span_end=11,
    )

    assert chunk.chunk_id == "test_0"
    assert chunk.text == "Sample text"
    assert chunk.token_count == 2
    assert chunk.char_count == 11
    assert chunk.metadata == {}


def test_text_chunk_with_metadata():
    """Test TextChunk with metadata."""
    chunk = TextChunk(
        chunk_id="test_0",
        text="Sample",
        token_count=1,
        char_count=6,
        chunk_index=0,
        span_start=0,
        span_end=6,
        metadata={"strategy": "token_aware", "custom": "value"},
    )

    assert chunk.metadata["strategy"] == "token_aware"
    assert chunk.metadata["custom"] == "value"


def test_chunker_config_defaults():
    """Test ChunkerConfig default values."""
    config = ChunkerConfig(strategy="token_aware")

    assert config.strategy == "token_aware"
    assert config.max_tokens == 512
    assert config.overlap_tokens == 50
    assert config.encoding_name == "cl100k_base"


def test_chunker_config_custom():
    """Test ChunkerConfig with custom values."""
    config = ChunkerConfig(strategy="fixed_size", chunk_size=2000, overlap_size=200)

    assert config.strategy == "fixed_size"
    assert config.chunk_size == 2000
    assert config.overlap_size == 200
