"""Tests for BaseEmbeddingProvider interface."""

from typing import Dict, List

from gundy_ai.embeddings import BaseEmbeddingProvider, EmbeddingResult


class MockProvider(BaseEmbeddingProvider):
    """Mock provider for testing interface."""

    def embed(self, texts: List[str]) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=[[0.1, 0.2] for _ in texts],
            model="mock",
            dimensions=2,
            total_tokens=len(texts),
            texts_count=len(texts),
            latency_ms=10.0,
            provider="mock",
        )

    def health_check(self) -> Dict[str, any]:
        return {"healthy": True, "provider": "mock", "model": "mock"}

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock"

    @property
    def dimensions(self) -> int:
        return 2


def test_base_provider_interface():
    """Test that BaseEmbeddingProvider interface can be implemented."""
    provider = MockProvider()

    assert hasattr(provider, "embed")
    assert hasattr(provider, "health_check")
    assert hasattr(provider, "provider_name")
    assert hasattr(provider, "model_name")
    assert hasattr(provider, "dimensions")


def test_base_provider_embed():
    """Test that embed method returns EmbeddingResult."""
    provider = MockProvider()
    result = provider.embed(["test"])

    assert isinstance(result, EmbeddingResult)
    assert len(result.embeddings) == 1
    assert len(result.embeddings[0]) == 2


def test_base_provider_health_check():
    """Test health_check method."""
    provider = MockProvider()
    health = provider.health_check()

    assert health["healthy"] is True
    assert health["provider"] == "mock"


def test_provider_properties():
    """Test provider properties."""
    provider = MockProvider()

    assert provider.provider_name == "mock"
    assert provider.model_name == "mock"
    assert provider.dimensions == 2


def test_provider_repr():
    """Test string representation."""
    provider = MockProvider()
    repr_str = repr(provider)

    assert "MockProvider" in repr_str
    assert "mock" in repr_str
