"""Tests for data models."""

from gundy_ai.vectorstore import QueryResult, StoreConfig, VectorDocument


def test_vector_document_creation():
    """Test creating a VectorDocument."""
    doc = VectorDocument(
        id="doc1",
        embedding=[0.1, 0.2, 0.3],
        metadata={"title": "Test"},
        text="Test text",
    )

    assert doc.id == "doc1"
    assert len(doc.embedding) == 3
    assert doc.metadata["title"] == "Test"
    assert doc.text == "Test text"


def test_vector_document_minimal():
    """Test VectorDocument with minimal fields."""
    doc = VectorDocument(id="doc1", embedding=[0.1, 0.2])

    assert doc.id == "doc1"
    assert doc.metadata == {}
    assert doc.text is None


def test_query_result_creation():
    """Test creating a QueryResult."""
    result = QueryResult(
        id="doc1", score=0.95, metadata={"title": "Test"}, text="Sample text"
    )

    assert result.id == "doc1"
    assert result.score == 0.95
    assert result.metadata["title"] == "Test"
    assert result.text == "Sample text"


def test_query_result_with_embedding():
    """Test QueryResult with embedding."""
    result = QueryResult(id="doc1", score=0.90, embedding=[0.1, 0.2, 0.3])

    assert result.embedding == [0.1, 0.2, 0.3]


def test_store_config_defaults():
    """Test StoreConfig default values."""
    config = StoreConfig(adapter_name="chromadb")

    assert config.adapter_name == "chromadb"
    assert config.collection_name == "documents"
    assert config.distance_metric == "cosine"


def test_store_config_custom():
    """Test StoreConfig with custom values."""
    config = StoreConfig(
        adapter_name="faiss",
        persist_directory="/path/to/db",
        collection_name="my_collection",
        embedding_dimension=1536,
        distance_metric="euclidean",
    )

    assert config.adapter_name == "faiss"
    assert config.persist_directory == "/path/to/db"
    assert config.collection_name == "my_collection"
    assert config.embedding_dimension == 1536
    assert config.distance_metric == "euclidean"
