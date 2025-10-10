"""Tests for BaseVectorStore interface."""

from typing import Any, Dict, List, Optional

from gundy_ai.vectorstore import BaseVectorStore, QueryResult


class MockVectorStore(BaseVectorStore):
    """Mock vector store for testing interface."""

    def __init__(self):
        self._vectors = {}

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        texts: Optional[List[str]] = None,
    ) -> None:
        for i, id in enumerate(ids):
            self._vectors[id] = {
                "embedding": embeddings[i],
                "metadata": metadatas[i] if metadatas else {},
                "text": texts[i] if texts else None,
            }

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter: Optional[Dict[str, Any]] = None,
        include_embeddings: bool = False,
    ) -> List[QueryResult]:
        return [
            QueryResult(
                id="doc1",
                score=0.95,
                metadata={"title": "Test"},
            )
        ]

    def delete(self, ids: List[str]) -> int:
        count = 0
        for id in ids:
            if id in self._vectors:
                del self._vectors[id]
                count += 1
        return count

    def count(self) -> int:
        return len(self._vectors)

    def health_check(self) -> Dict[str, Any]:
        return {"healthy": True, "adapter": "mock", "collection": "test"}

    @property
    def adapter_name(self) -> str:
        return "mock"

    @property
    def collection_name(self) -> str:
        return "test"


def test_base_vectorstore_interface():
    """Test that BaseVectorStore interface can be implemented."""
    store = MockVectorStore()

    assert hasattr(store, "upsert")
    assert hasattr(store, "query")
    assert hasattr(store, "delete")
    assert hasattr(store, "count")
    assert hasattr(store, "health_check")


def test_base_vectorstore_upsert():
    """Test upsert method."""
    store = MockVectorStore()

    store.upsert(
        ids=["doc1", "doc2"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        metadatas=[{"title": "Doc 1"}, {"title": "Doc 2"}],
    )

    assert store.count() == 2


def test_base_vectorstore_query():
    """Test query method."""
    store = MockVectorStore()

    results = store.query(query_embedding=[0.1, 0.2], top_k=5)

    assert len(results) > 0
    assert isinstance(results[0], QueryResult)


def test_base_vectorstore_delete():
    """Test delete method."""
    store = MockVectorStore()

    store.upsert(ids=["doc1"], embeddings=[[0.1, 0.2]])
    deleted = store.delete(["doc1"])

    assert deleted == 1
    assert store.count() == 0


def test_base_vectorstore_count():
    """Test count method."""
    store = MockVectorStore()

    assert store.count() == 0

    store.upsert(ids=["doc1", "doc2"], embeddings=[[0.1], [0.2]])

    assert store.count() == 2


def test_base_vectorstore_health_check():
    """Test health_check method."""
    store = MockVectorStore()

    health = store.health_check()

    assert health["healthy"] is True


def test_vectorstore_properties():
    """Test adapter properties."""
    store = MockVectorStore()

    assert store.adapter_name == "mock"
    assert store.collection_name == "test"


def test_vectorstore_repr():
    """Test string representation."""
    store = MockVectorStore()

    repr_str = repr(store)

    assert "MockVectorStore" in repr_str
    assert "mock" in repr_str
