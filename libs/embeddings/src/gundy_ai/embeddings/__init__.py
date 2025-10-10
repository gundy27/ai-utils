"""Embedding generation for AI applications."""

from .audit import EmbeddingAuditEvent, EmbeddingEventType, emit_embedding_event
from .base import BaseEmbeddingProvider
from .models import EmbeddingResult, ProviderConfig

__version__ = "0.1.0"

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingResult",
    "ProviderConfig",
    "EmbeddingAuditEvent",
    "EmbeddingEventType",
    "emit_embedding_event",
]

# Import providers conditionally
from importlib.util import find_spec

if find_spec("openai") is not None:
    try:
        from .providers import OpenAIEmbeddingProvider  # noqa: F401

        __all__.append("OpenAIEmbeddingProvider")
    except ImportError:
        pass
