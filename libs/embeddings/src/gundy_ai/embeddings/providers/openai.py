"""OpenAI embedding provider."""

from __future__ import annotations

import os
import time
from typing import Dict, List, Optional

import structlog

from ..audit import EmbeddingEventType, emit_embedding_event
from ..base import BaseEmbeddingProvider
from ..models import EmbeddingResult

logger = structlog.get_logger(__name__)


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider with batch support and retries.

    Supports all OpenAI embedding models including:
    - text-embedding-3-small (1536 dims, $0.02/1M tokens)
    - text-embedding-3-large (3072 dims, $0.13/1M tokens)
    - text-embedding-ada-002 (1536 dims, $0.10/1M tokens)

    Example:
        provider = OpenAIEmbeddingProvider(
            api_key="your-key",
            model="text-embedding-3-small"
        )
        result = provider.embed(["text1", "text2"])
    """

    # Model dimensions mapping
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    # Cost per 1M tokens (USD)
    MODEL_COSTS = {
        "text-embedding-3-small": 0.02,
        "text-embedding-3-large": 0.13,
        "text-embedding-ada-002": 0.10,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        api_base: Optional[str] = None,
        max_batch_size: int = 100,
        timeout_seconds: int = 60,
        max_retries: int = 3,
    ):
        """Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
            model: Model name (default: text-embedding-3-small)
            api_base: Custom API base URL (optional)
            max_batch_size: Maximum texts per batch (default: 100)
            timeout_seconds: Request timeout (default: 60)
            max_retries: Maximum retry attempts (default: 3)

        Raises:
            ValueError: If API key is missing
            RuntimeError: If openai package is not installed
        """
        # Get API key from parameter or environment
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.api_base = api_base
        self.max_batch_size = max_batch_size
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        # Lazy import openai to allow package to load even if not installed
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "openai package required for OpenAI provider. "
                "Install with: pip install 'gundy-ai-embeddings[openai]'"
            ) from e

        # Initialize client
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=api_base,
            timeout=timeout_seconds,
            max_retries=max_retries,
        )

        logger.info(
            "openai_provider_initialized",
            model=model,
            max_batch_size=max_batch_size,
            dimensions=self.dimensions,
        )

    @property
    def provider_name(self) -> str:
        """Get provider name."""
        return "openai"

    @property
    def model_name(self) -> str:
        """Get model name."""
        return self.model

    @property
    def dimensions(self) -> int:
        """Get embedding dimensions for current model."""
        return self.MODEL_DIMENSIONS.get(self.model, 1536)

    def embed(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for texts.

        Automatically handles batching if texts exceed max_batch_size.

        Args:
            texts: List of texts to embed

        Returns:
            EmbeddingResult with embeddings and metadata

        Raises:
            ValueError: If texts list is empty
            RuntimeError: If embedding generation fails after retries
        """
        start_time = time.time()

        if not texts:
            raise ValueError("texts list cannot be empty")

        # Emit requested event
        emit_embedding_event(
            event_type=EmbeddingEventType.EMBEDDING_REQUESTED,
            provider=self.provider_name,
            model=self.model,
            outcome="pending",
            texts_count=len(texts),
            batch_size=min(len(texts), self.max_batch_size),
        )

        try:
            logger.info(
                "embedding_started",
                provider=self.provider_name,
                model=self.model,
                texts_count=len(texts),
                max_batch_size=self.max_batch_size,
            )

            # Process in batches if needed
            all_embeddings = []
            total_tokens = 0

            for i in range(0, len(texts), self.max_batch_size):
                batch = texts[i : i + self.max_batch_size]
                batch_num = i // self.max_batch_size + 1
                total_batches = (
                    len(texts) + self.max_batch_size - 1
                ) // self.max_batch_size

                logger.debug(
                    "processing_batch",
                    batch=batch_num,
                    total_batches=total_batches,
                    batch_size=len(batch),
                )

                # Call OpenAI API
                response = self.client.embeddings.create(input=batch, model=self.model)

                # Extract embeddings and token count
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                total_tokens += response.usage.total_tokens

                logger.debug(
                    "batch_completed",
                    batch=batch_num,
                    embeddings=len(batch_embeddings),
                    tokens=response.usage.total_tokens,
                )

            latency_ms = (time.time() - start_time) * 1000

            # Calculate estimated cost
            cost_per_million = self.MODEL_COSTS.get(self.model, 0.10)
            estimated_cost = (total_tokens / 1_000_000) * cost_per_million

            result = EmbeddingResult(
                embeddings=all_embeddings,
                model=self.model,
                dimensions=self.dimensions,
                total_tokens=total_tokens,
                texts_count=len(texts),
                latency_ms=latency_ms,
                estimated_cost_usd=estimated_cost,
                provider=self.provider_name,
                metadata={
                    "batches_processed": total_batches,
                    "max_batch_size": self.max_batch_size,
                },
            )

            logger.info(
                "embedding_completed",
                texts=len(texts),
                embeddings=len(all_embeddings),
                tokens=total_tokens,
                latency_ms=latency_ms,
                cost_usd=estimated_cost,
            )

            # Emit completed event
            emit_embedding_event(
                event_type=EmbeddingEventType.EMBEDDING_COMPLETED,
                provider=self.provider_name,
                model=self.model,
                outcome="success",
                texts_count=len(texts),
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                estimated_cost_usd=estimated_cost,
                metadata={"dimensions": self.dimensions},
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = f"Embedding generation failed: {str(e)}"

            logger.error("embedding_failed", error=str(e), latency_ms=latency_ms)

            emit_embedding_event(
                event_type=EmbeddingEventType.EMBEDDING_FAILED,
                provider=self.provider_name,
                model=self.model,
                outcome="error",
                texts_count=len(texts),
                latency_ms=latency_ms,
                error_message=error_msg,
            )

            raise RuntimeError(error_msg) from e

    def health_check(self) -> Dict[str, any]:
        """Check if OpenAI API is accessible.

        Makes a minimal embedding request to verify connectivity.

        Returns:
            Health status dictionary
        """
        start_time = time.time()

        try:
            # Try a minimal embedding request
            response = self.client.embeddings.create(
                input=["health check"], model=self.model
            )

            latency_ms = (time.time() - start_time) * 1000

            result = {
                "healthy": True,
                "provider": self.provider_name,
                "model": self.model,
                "dimensions": len(response.data[0].embedding),
                "latency_ms": latency_ms,
            }

            logger.info("health_check_passed", **result)

            emit_embedding_event(
                event_type=EmbeddingEventType.PROVIDER_HEALTH_CHECK,
                provider=self.provider_name,
                model=self.model,
                outcome="success",
                latency_ms=latency_ms,
                metadata={"healthy": True},
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = {
                "healthy": False,
                "provider": self.provider_name,
                "model": self.model,
                "error": str(e),
                "latency_ms": latency_ms,
            }

            logger.error("health_check_failed", error=str(e))

            emit_embedding_event(
                event_type=EmbeddingEventType.PROVIDER_HEALTH_CHECK,
                provider=self.provider_name,
                model=self.model,
                outcome="failure",
                latency_ms=latency_ms,
                error_message=str(e),
                metadata={"healthy": False},
            )

            return result
