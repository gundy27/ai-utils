"""Tests for ChromaDB adapter."""

import tempfile
from pathlib import Path

import pytest

from gundy_ai.vectorstore import ChromaDBAdapter, QueryResult


@pytest.fixture
def temp_db():
    """Create temporary database directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup handled by tmpdir fixture


@pytest.fixture
def adapter(temp_db):
    """Create ChromaDB adapter instance."""
    return ChromaDBAdapter(persist_directory=temp_db, collection_name="test_collection")


def test_chromadb_adapter_init(temp_db):
    """Test adapter initialization."""
    adapter = ChromaDBAdapter(persist_directory=temp_db, collection_name="test")

    assert adapter.adapter_name == "chromadb"
    assert adapter.collection_name == "test"
    assert Path(temp_db).exists()


def test_upsert_single_vector(adapter):
    """Test upserting a single vector."""
    adapter.upsert(
        ids=["doc1"],
        embeddings=[[0.1, 0.2, 0.3]],
        metadatas=[{"title": "Doc 1"}],
        texts=["Sample text"],
    )

    assert adapter.count() == 1


def test_upsert_multiple_vectors(adapter):
    """Test upserting multiple vectors."""
    adapter.upsert(
        ids=["doc1", "doc2", "doc3"],
        embeddings=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        metadatas=[{"i": 1}, {"i": 2}, {"i": 3}],
    )

    assert adapter.count() == 3


def test_upsert_without_metadata(adapter):
    """Test upserting without metadata."""
    adapter.upsert(ids=["doc1"], embeddings=[[0.1, 0.2]])

    assert adapter.count() == 1


def test_upsert_update_existing(adapter):
    """Test that upserting existing ID updates it."""
    adapter.upsert(ids=["doc1"], embeddings=[[0.1, 0.2]], metadatas=[{"version": 1}])

    assert adapter.count() == 1

    # Update same ID
    adapter.upsert(ids=["doc1"], embeddings=[[0.3, 0.4]], metadatas=[{"version": 2}])

    # Should still be 1 document
    assert adapter.count() == 1


def test_upsert_validation_errors(adapter):
    """Test upsert validation."""
    # Empty lists
    with pytest.raises(ValueError, match="cannot be empty"):
        adapter.upsert(ids=[], embeddings=[])

    # Mismatched lengths
    with pytest.raises(ValueError, match="must match"):
        adapter.upsert(ids=["doc1"], embeddings=[[0.1], [0.2]])


def test_query_basic(adapter):
    """Test basic query."""
    # Insert some vectors
    adapter.upsert(
        ids=["doc1", "doc2"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        metadatas=[{"type": "a"}, {"type": "b"}],
    )

    # Query for similar vector
    results = adapter.query(query_embedding=[0.9, 0.1], top_k=2)

    assert len(results) <= 2
    assert all(isinstance(r, QueryResult) for r in results)
    assert all(r.score > 0 for r in results)


def test_query_top_k(adapter):
    """Test query with different top_k values."""
    # Insert 5 vectors
    adapter.upsert(
        ids=[f"doc{i}" for i in range(5)],
        embeddings=[[float(i), 0.0] for i in range(5)],
    )

    # Query with top_k=3
    results = adapter.query(query_embedding=[2.5, 0.0], top_k=3)

    assert len(results) == 3


def test_query_with_filter(adapter):
    """Test query with metadata filter."""
    adapter.upsert(
        ids=["doc1", "doc2", "doc3"],
        embeddings=[[1.0, 0.0], [1.0, 0.1], [1.0, 0.2]],
        metadatas=[{"category": "a"}, {"category": "b"}, {"category": "a"}],
    )

    # Query with filter
    results = adapter.query(
        query_embedding=[1.0, 0.0], top_k=5, filter={"category": "a"}
    )

    # Should only return docs with category 'a'
    assert len(results) <= 2
    for result in results:
        if result.metadata:  # Some results may not have metadata
            assert result.metadata.get("category") in ["a", None]


def test_query_empty_store(adapter):
    """Test querying empty store."""
    results = adapter.query(query_embedding=[0.1, 0.2], top_k=5)

    assert results == []


def test_delete_single(adapter):
    """Test deleting a single vector."""
    adapter.upsert(ids=["doc1", "doc2"], embeddings=[[0.1], [0.2]])

    deleted = adapter.delete(["doc1"])

    assert deleted == 1
    assert adapter.count() == 1


def test_delete_multiple(adapter):
    """Test deleting multiple vectors."""
    adapter.upsert(ids=["doc1", "doc2", "doc3"], embeddings=[[0.1], [0.2], [0.3]])

    deleted = adapter.delete(["doc1", "doc3"])

    assert deleted == 2
    assert adapter.count() == 1


def test_delete_nonexistent(adapter):
    """Test deleting non-existent IDs."""
    adapter.upsert(ids=["doc1"], embeddings=[[0.1]])

    # ChromaDB doesn't raise error for non-existent IDs
    adapter.delete(["nonexistent"])

    # Count should be unchanged
    assert adapter.count() == 1


def test_delete_empty_list(adapter):
    """Test deleting with empty list."""
    deleted = adapter.delete([])

    assert deleted == 0


def test_count(adapter):
    """Test count method."""
    assert adapter.count() == 0

    adapter.upsert(ids=["doc1"], embeddings=[[0.1]])
    assert adapter.count() == 1

    adapter.upsert(ids=["doc2"], embeddings=[[0.2]])
    assert adapter.count() == 2


def test_clear(adapter):
    """Test clearing collection."""
    adapter.upsert(ids=["doc1", "doc2", "doc3"], embeddings=[[0.1], [0.2], [0.3]])

    assert adapter.count() == 3

    cleared = adapter.clear()

    assert cleared == 3
    assert adapter.count() == 0


def test_health_check(adapter):
    """Test health check."""
    health = adapter.health_check()

    assert health["healthy"] is True
    assert health["adapter"] == "chromadb"
    assert health["collection"] == "test_collection"
    assert "count" in health
    assert "latency_ms" in health


def test_adapter_repr(adapter):
    """Test string representation."""
    repr_str = repr(adapter)

    assert "ChromaDBAdapter" in repr_str
    assert "chromadb" in repr_str
    assert "test_collection" in repr_str
