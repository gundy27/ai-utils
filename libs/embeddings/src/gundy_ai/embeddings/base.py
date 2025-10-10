"""Base embedding provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from .models import EmbeddingResult


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    All embedding providers must implement this interface to be compatible
    with the embedding system. Providers are responsible for generating
    vector embeddings from text using their specific API.

    Example:
        class MyProvider(BaseEmbeddingProvider):
            def embed(self, texts: List[str]) -> EmbeddingResult:
                # Implementation here
                pass

            def health_check(self) -> Dict[str, any]:
                # Implementation here
                pass
    """

    @abstractmethod
    def embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            EmbeddingResult with:
            - embeddings: List of embedding vectors
            - model: Model used
            - dimensions: Embedding dimensionality
            - total_tokens: Tokens processed
            - texts_count: Number of texts
            - latency_ms: Processing time
            - estimated_cost_usd: Estimated cost (if available)
            - provider: Provider name
            - metadata: Provider-specific info

        Raises:
            ValueError: If texts list is empty or invalid
            RuntimeError: If embedding generation fails
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, any]:
        """Check if provider is healthy and accessible.

        Returns:
            Dictionary with health status:
            - healthy: bool
            - provider: str
            - model: str
            - error: Optional[str]
            - latency_ms: Optional[float]

        Example:
            {
                "healthy": True,
                "provider": "openai",
                "model": "text-embedding-3-small",
                "latency_ms": 120.5
            }
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Get provider name.

        Returns:
            Provider identifier (e.g., "openai", "cohere")
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get model name.

        Returns:
            Model identifier being used
        """
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Get embedding dimensions.

        Returns:
            Number of dimensions in embeddings
        """
        pass

    def __repr__(self) -> str:
        """String representation of provider."""
        return f"{self.__class__.__name__}(provider={self.provider_name}, model={self.model_name})"
