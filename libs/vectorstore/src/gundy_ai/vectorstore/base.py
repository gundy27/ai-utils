"""Base vector store interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from .models import QueryResult


class BaseVectorStore(ABC):
    """Abstract base class for vector store adapters.

    All vector store implementations must implement this interface.
    Provides unified API for upserting, querying, and managing vectors
    across different vector database backends.

    Example:
        class MyVectorStore(BaseVectorStore):
            def upsert(self, ids, embeddings, metadatas=None, texts=None):
                # Implementation
                pass

            def query(self, query_embedding, top_k=10, filter=None):
                # Implementation
                pass
    """

    @abstractmethod
    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        texts: Optional[List[str]] = None,
    ) -> None:
        """Upsert vectors with metadata.

        Args:
            ids: List of unique document identifiers
            embeddings: List of embedding vectors
            metadatas: Optional list of metadata dicts
            texts: Optional list of original texts

        Raises:
            ValueError: If ids/embeddings lengths don't match
            RuntimeError: If upsert operation fails
        """
        pass

    @abstractmethod
    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        include_embeddings: bool = False,
    ) -> List[QueryResult]:
        """Query for similar vectors.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter: Optional metadata filter
            include_embeddings: Include embeddings in results

        Returns:
            List of QueryResult objects sorted by similarity (highest first)

        Raises:
            ValueError: If query_embedding is invalid
            RuntimeError: If query operation fails
        """
        pass

    @abstractmethod
    def delete(self, ids: List[str]) -> int:
        """Delete vectors by IDs.

        Args:
            ids: List of document IDs to delete

        Returns:
            Number of documents deleted

        Raises:
            RuntimeError: If delete operation fails
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Get total number of vectors in store.

        Returns:
            Number of vectors

        Raises:
            RuntimeError: If count operation fails
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Check if vector store is healthy.

        Returns:
            Health status dictionary with:
            - healthy: bool
            - adapter: str
            - collection: str
            - count: Optional[int]
            - error: Optional[str]
        """
        pass

    @property
    @abstractmethod
    def adapter_name(self) -> str:
        """Get adapter name.

        Returns:
            Adapter identifier (e.g., "chromadb", "faiss")
        """
        pass

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """Get collection/index name.

        Returns:
            Collection name
        """
        pass

    def clear(self) -> int:
        """Clear all vectors from store.

        Returns:
            Number of vectors deleted

        Raises:
            RuntimeError: If clear operation fails
        """
        count = self.count()
        # Default implementation: get all IDs and delete
        # Subclasses can override for more efficient clearing
        return count

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(adapter={self.adapter_name}, collection={self.collection_name})"
