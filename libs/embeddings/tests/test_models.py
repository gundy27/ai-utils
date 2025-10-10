"""Tests for data models."""

from gundy_ai.embeddings import EmbeddingResult, ProviderConfig


def test_embedding_result_creation():
    """Test creating an EmbeddingResult."""
    result = EmbeddingResult(
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        model="test-model",
        dimensions=2,
        total_tokens=10,
        texts_count=2,
        latency_ms=100.5,
        provider="test",
    )

    assert len(result.embeddings) == 2
    assert result.model == "test-model"
    assert result.dimensions == 2
    assert result.total_tokens == 10
    assert result.texts_count == 2
    assert result.latency_ms == 100.5
    assert result.provider == "test"


def test_embedding_result_with_cost():
    """Test EmbeddingResult with cost estimation."""
    result = EmbeddingResult(
        embeddings=[[0.1]],
        model="test-model",
        dimensions=1,
        total_tokens=5,
        texts_count=1,
        latency_ms=50.0,
        estimated_cost_usd=0.00001,
        provider="test",
    )

    assert result.estimated_cost_usd == 0.00001


def test_provider_config_defaults():
    """Test ProviderConfig default values."""
    config = ProviderConfig(provider_name="test", model="test-model")

    assert config.provider_name == "test"
    assert config.model == "test-model"
    assert config.max_batch_size == 100
    assert config.timeout_seconds == 60
    assert config.max_retries == 3


def test_provider_config_custom():
    """Test ProviderConfig with custom values."""
    config = ProviderConfig(
        provider_name="openai",
        model="text-embedding-3-small",
        api_key="sk-test",
        max_batch_size=50,
        timeout_seconds=120,
        max_retries=5,
    )

    assert config.api_key == "sk-test"
    assert config.max_batch_size == 50
    assert config.timeout_seconds == 120
    assert config.max_retries == 5
