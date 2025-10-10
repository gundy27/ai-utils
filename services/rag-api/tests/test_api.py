"""Basic API tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_health():
    """Test health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
    assert "timestamp" in data


def test_stats():
    """Test stats endpoint."""
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "vector_count" in data
    assert "embedding_model" in data


@pytest.mark.skipif(True, reason="Requires OPENAI_API_KEY - run manually")
def test_ingest_and_search():
    """Test document ingestion and search flow."""
    # Create a simple test document
    test_content = "Machine learning is a subset of artificial intelligence."

    # Ingest document
    files = {"file": ("test.txt", test_content.encode(), "text/plain")}
    response = client.post(
        "/documents/ingest",
        files=files,
        data={"metadata": '{"source": "test"}'},
    )

    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert "chunks_created" in data

    # Search for it
    search_response = client.post(
        "/search",
        json={
            "query": "What is machine learning?",
            "top_k": 5,
        },
    )

    assert search_response.status_code == 200
    search_data = search_response.json()
    assert "results" in search_data
    assert len(search_data["results"]) > 0
