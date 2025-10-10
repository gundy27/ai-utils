"""Vector store adapters for AI applications."""

from .audit import VectorStoreAuditEvent, VectorStoreEventType, emit_vectorstore_event
from .base import BaseVectorStore
from .models import QueryResult, StoreConfig, VectorDocument

__version__ = "0.1.0"

__all__ = [
    "BaseVectorStore",
    "VectorDocument",
    "QueryResult",
    "StoreConfig",
    "VectorStoreAuditEvent",
    "VectorStoreEventType",
    "emit_vectorstore_event",
]

# Import adapters conditionally
from importlib.util import find_spec

if find_spec("chromadb") is not None:
    try:
        from .adapters import ChromaDBAdapter  # noqa: F401

        __all__.append("ChromaDBAdapter")
    except ImportError:
        pass
