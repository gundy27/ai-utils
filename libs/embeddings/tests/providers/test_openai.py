"""Tests for OpenAI embedding provider."""

import os

import pytest

from gundy_ai.embeddings import EmbeddingResult, OpenAIEmbeddingProvider


# Skip tests if OPENAI_API_KEY not set
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set - skipping live API tests",
)


@pytest.fixture
def provider():
    """Create OpenAI provider instance."""
    return OpenAIEmbeddingProvider(model="text-embedding-3-small")


def test_openai_provider_init():
    """Test provider initialization."""
    provider = OpenAIEmbeddingProvider(
        api_key=os.environ.get("OPENAI_API_KEY"), model="text-embedding-3-small"
    )

    assert provider.provider_name == "openai"
    assert provider.model_name == "text-embedding-3-small"
    assert provider.dimensions == 1536


def test_openai_provider_init_no_api_key():
    """Test that missing API key raises error."""
    # Temporarily remove API key
    old_key = os.environ.get("OPENAI_API_KEY")
    if old_key:
        del os.environ["OPENAI_API_KEY"]

    try:
        with pytest.raises(ValueError, match="API key required"):
            OpenAIEmbeddingProvider(model="text-embedding-3-small")
    finally:
        if old_key:
            os.environ["OPENAI_API_KEY"] = old_key


def test_embed_single_text(provider):
    """Test embedding single text."""
    result = provider.embed(["Hello world"])

    assert isinstance(result, EmbeddingResult)
    assert len(result.embeddings) == 1
    assert len(result.embeddings[0]) == 1536
    assert result.texts_count == 1
    assert result.total_tokens > 0
    assert result.latency_ms > 0
    assert result.estimated_cost_usd > 0


def test_embed_multiple_texts(provider):
    """Test embedding multiple texts."""
    texts = ["First text", "Second text", "Third text"]

    result = provider.embed(texts)

    assert len(result.embeddings) == 3
    assert all(len(emb) == 1536 for emb in result.embeddings)
    assert result.texts_count == 3
    assert result.total_tokens > 0


def test_embed_empty_list_raises_error(provider):
    """Test that empty text list raises error."""
    with pytest.raises(ValueError, match="cannot be empty"):
        provider.embed([])


def test_embed_batch_processing(provider):
    """Test that large batches are processed correctly."""
    # Create more texts than max_batch_size
    texts = [f"Text number {i}" for i in range(150)]

    result = provider.embed(texts)

    assert len(result.embeddings) == 150
    assert result.texts_count == 150
    # Should have processed in 2 batches
    assert result.metadata["batches_processed"] == 2


def test_health_check(provider):
    """Test health check."""
    health = provider.health_check()

    assert health["healthy"] is True
    assert health["provider"] == "openai"
    assert health["model"] == "text-embedding-3-small"
    assert health["dimensions"] == 1536
    assert health["latency_ms"] > 0


def test_model_dimensions():
    """Test that different models have correct dimensions."""
    # Test small model
    provider_small = OpenAIEmbeddingProvider(model="text-embedding-3-small")
    assert provider_small.dimensions == 1536

    # Test large model (dimensions, not actual API call)
    provider_large = OpenAIEmbeddingProvider(model="text-embedding-3-large")
    assert provider_large.dimensions == 3072


def test_cost_estimation(provider):
    """Test cost estimation."""
    result = provider.embed(["test text"])

    # Cost should be calculated
    assert result.estimated_cost_usd is not None
    assert result.estimated_cost_usd > 0
    # Should be very small for one text
    assert result.estimated_cost_usd < 0.001


def test_provider_repr():
    """Test string representation."""
    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")

    repr_str = repr(provider)

    assert "OpenAIEmbeddingProvider" in repr_str
    assert "openai" in repr_str
    assert "text-embedding-3-small" in repr_str
