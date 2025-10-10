"""ChromaDB vector store adapter."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from ..audit import VectorStoreEventType, emit_vectorstore_event
from ..base import BaseVectorStore
from ..models import QueryResult

logger = structlog.get_logger(__name__)


class ChromaDBAdapter(BaseVectorStore):
    """ChromaDB vector store adapter.

    Provides persistent vector storage using ChromaDB with
    automatic persistence to disk.

    Example:
        store = ChromaDBAdapter(
            persist_directory="./vector_db",
            collection_name="documents"
        )
        store.upsert(
            ids=["doc1"],
            embeddings=[[0.1, 0.2, 0.3]],
            metadatas=[{"title": "Doc 1"}]
        )
    """

    def __init__(
        self,
        persist_directory: str = "./vector_db",
        collection_name: str = "documents",
        distance_metric: str = "cosine",
    ):
        """Initialize ChromaDB adapter.

        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of collection
            distance_metric: Distance metric (cosine, l2, ip)

        Raises:
            RuntimeError: If ChromaDB is not installed
        """
        self.persist_directory = Path(persist_directory)
        self._collection_name = collection_name
        self.distance_metric = distance_metric

        # Import ChromaDB (late import to allow package to load)
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as e:
            raise RuntimeError(
                "chromadb package required. "
                "Install with: pip install 'gundy-ai-vectorstore[chromadb]'"
            ) from e

        # Map distance metrics
        metric_map = {
            "cosine": "cosine",
            "l2": "l2",
            "euclidean": "l2",
            "dot": "ip",
            "ip": "ip",
        }
        chroma_metric = metric_map.get(distance_metric, "cosine")

        # Create persist directory
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False),
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": chroma_metric}
        )

        logger.info(
            "chromadb_adapter_initialized",
            persist_directory=str(self.persist_directory),
            collection=collection_name,
            distance_metric=distance_metric,
        )

    @property
    def adapter_name(self) -> str:
        """Get adapter name."""
        return "chromadb"

    @property
    def collection_name(self) -> str:
        """Get collection name."""
        return self._collection_name

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        texts: Optional[List[str]] = None,
    ) -> None:
        """Upsert vectors into ChromaDB.

        Args:
            ids: Document IDs
            embeddings: Embedding vectors
            metadatas: Optional metadata dicts
            texts: Optional original texts

        Raises:
            ValueError: If input validation fails
            RuntimeError: If upsert fails
        """
        start_time = time.time()

        if not ids or not embeddings:
            raise ValueError("ids and embeddings cannot be empty")

        if len(ids) != len(embeddings):
            raise ValueError(
                f"ids length ({len(ids)}) must match embeddings length ({len(embeddings)})"
            )

        if metadatas and len(metadatas) != len(ids):
            raise ValueError(
                f"metadatas length ({len(metadatas)}) must match ids length ({len(ids)})"
            )

        if texts and len(texts) != len(ids):
            raise ValueError(
                f"texts length ({len(texts)}) must match ids length ({len(ids)})"
            )

        try:
            logger.info(
                "vectorstore_upsert_started",
                adapter=self.adapter_name,
                collection=self._collection_name,
                vector_count=len(ids),
            )

            # Prepare documents for ChromaDB
            documents = texts if texts else [None] * len(ids)

            # ChromaDB requires non-empty metadata dicts
            # Add default "_indexed" field if metadata is empty
            if metadatas:
                metadatas = [meta if meta else {"_indexed": True} for meta in metadatas]
            else:
                metadatas = [{"_indexed": True}] * len(ids)

            # Upsert to collection
            self.collection.upsert(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents
            )

            latency_ms = (time.time() - start_time) * 1000

            logger.info(
                "vectorstore_upsert_completed",
                vector_count=len(ids),
                latency_ms=latency_ms,
            )

            # Emit audit event (embeddings redacted automatically)
            emit_vectorstore_event(
                event_type=VectorStoreEventType.VECTORSTORE_UPSERT,
                adapter=self.adapter_name,
                collection=self._collection_name,
                operation="upsert",
                outcome="success",
                vector_count=len(ids),
                latency_ms=latency_ms,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = f"Upsert failed: {str(e)}"

            logger.error("vectorstore_upsert_failed", error=str(e))

            emit_vectorstore_event(
                event_type=VectorStoreEventType.VECTORSTORE_UPSERT,
                adapter=self.adapter_name,
                collection=self._collection_name,
                operation="upsert",
                outcome="error",
                vector_count=len(ids),
                latency_ms=latency_ms,
                error_message=error_msg,
            )

            raise RuntimeError(error_msg) from e

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        include_embeddings: bool = False,
    ) -> List[QueryResult]:
        """Query ChromaDB for similar vectors.

        Args:
            query_embedding: Query vector
            top_k: Number of results
            filter: Metadata filter (ChromaDB where clause)
            include_embeddings: Include embeddings in results

        Returns:
            List of QueryResult objects

        Raises:
            ValueError: If query_embedding is invalid
            RuntimeError: If query fails
        """
        start_time = time.time()

        if not query_embedding:
            raise ValueError("query_embedding cannot be empty")

        try:
            logger.info(
                "vectorstore_query_started",
                adapter=self.adapter_name,
                collection=self._collection_name,
                top_k=top_k,
                filter_applied=filter is not None,
            )

            # Query collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter,
                include=["documents", "metadatas", "distances"]
                + (["embeddings"] if include_embeddings else []),
            )

            latency_ms = (time.time() - start_time) * 1000

            # Convert to QueryResult objects
            query_results = []

            if results["ids"] and results["ids"][0]:
                for i, id in enumerate(results["ids"][0]):
                    # ChromaDB returns distances (lower = more similar)
                    # Convert to score (higher = more similar) using 1 / (1 + distance)
                    distance = results["distances"][0][i]
                    score = 1.0 / (1.0 + distance)

                    query_results.append(
                        QueryResult(
                            id=id,
                            score=score,
                            metadata=(
                                results["metadatas"][0][i]
                                if results["metadatas"]
                                else {}
                            ),
                            text=(
                                results["documents"][0][i]
                                if results["documents"]
                                else None
                            ),
                            embedding=(
                                results.get("embeddings", [[]])[0][i]
                                if include_embeddings
                                else None
                            ),
                        )
                    )

            logger.info(
                "vectorstore_query_completed",
                results_found=len(query_results),
                latency_ms=latency_ms,
            )

            # Emit audit event (query embedding redacted automatically)
            emit_vectorstore_event(
                event_type=VectorStoreEventType.VECTORSTORE_QUERY,
                adapter=self.adapter_name,
                collection=self._collection_name,
                operation="query",
                outcome="success",
                top_k=top_k,
                filter_applied=filter is not None,
                latency_ms=latency_ms,
                metadata={"results_found": len(query_results)},
            )

            return query_results

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = f"Query failed: {str(e)}"

            logger.error("vectorstore_query_failed", error=str(e))

            emit_vectorstore_event(
                event_type=VectorStoreEventType.VECTORSTORE_QUERY,
                adapter=self.adapter_name,
                collection=self._collection_name,
                operation="query",
                outcome="error",
                top_k=top_k,
                latency_ms=latency_ms,
                error_message=error_msg,
            )

            raise RuntimeError(error_msg) from e

    def delete(self, ids: List[str]) -> int:
        """Delete vectors by IDs.

        Args:
            ids: Document IDs to delete

        Returns:
            Number of documents deleted

        Raises:
            RuntimeError: If delete fails
        """
        start_time = time.time()

        if not ids:
            return 0

        try:
            logger.info(
                "vectorstore_delete_started",
                adapter=self.adapter_name,
                collection=self._collection_name,
                vector_count=len(ids),
            )

            self.collection.delete(ids=ids)

            latency_ms = (time.time() - start_time) * 1000

            logger.info(
                "vectorstore_delete_completed", deleted=len(ids), latency_ms=latency_ms
            )

            # Emit audit event
            emit_vectorstore_event(
                event_type=VectorStoreEventType.VECTORSTORE_DELETE,
                adapter=self.adapter_name,
                collection=self._collection_name,
                operation="delete",
                outcome="success",
                vector_count=len(ids),
                latency_ms=latency_ms,
            )

            return len(ids)

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_msg = f"Delete failed: {str(e)}"

            logger.error("vectorstore_delete_failed", error=str(e))

            emit_vectorstore_event(
                event_type=VectorStoreEventType.VECTORSTORE_DELETE,
                adapter=self.adapter_name,
                collection=self._collection_name,
                operation="delete",
                outcome="error",
                vector_count=len(ids),
                latency_ms=latency_ms,
                error_message=error_msg,
            )

            raise RuntimeError(error_msg) from e

    def count(self) -> int:
        """Get count of vectors in collection.

        Returns:
            Number of vectors

        Raises:
            RuntimeError: If count fails
        """
        try:
            return self.collection.count()
        except Exception as e:
            logger.error("vectorstore_count_failed", error=str(e))
            raise RuntimeError(f"Count failed: {str(e)}") from e

    def health_check(self) -> Dict[str, Any]:
        """Check if ChromaDB is accessible.

        Returns:
            Health status dictionary
        """
        start_time = time.time()

        try:
            count = self.collection.count()
            latency_ms = (time.time() - start_time) * 1000

            result = {
                "healthy": True,
                "adapter": self.adapter_name,
                "collection": self._collection_name,
                "count": count,
                "latency_ms": latency_ms,
            }

            logger.info("health_check_passed", **result)

            emit_vectorstore_event(
                event_type=VectorStoreEventType.VECTORSTORE_HEALTH_CHECK,
                adapter=self.adapter_name,
                collection=self._collection_name,
                operation="health_check",
                outcome="success",
                latency_ms=latency_ms,
                metadata={"count": count},
            )

            return result

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000

            result = {
                "healthy": False,
                "adapter": self.adapter_name,
                "collection": self._collection_name,
                "error": str(e),
                "latency_ms": latency_ms,
            }

            logger.error("health_check_failed", error=str(e))

            emit_vectorstore_event(
                event_type=VectorStoreEventType.VECTORSTORE_HEALTH_CHECK,
                adapter=self.adapter_name,
                collection=self._collection_name,
                operation="health_check",
                outcome="failure",
                latency_ms=latency_ms,
                error_message=str(e),
            )

            return result

    def clear(self) -> int:
        """Clear all vectors from collection.

        Returns:
            Number of vectors deleted
        """
        try:
            count = self.count()
            if count > 0:
                # Delete collection and recreate
                self.client.delete_collection(name=self._collection_name)
                self.collection = self.client.create_collection(
                    name=self._collection_name
                )
                logger.info("collection_cleared", count=count)
            return count
        except Exception as e:
            logger.error("collection_clear_failed", error=str(e))
            raise RuntimeError(f"Clear failed: {str(e)}") from e
