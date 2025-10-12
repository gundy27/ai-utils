"""Tests for streaming chat endpoint."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_chat_stream_pipeline():
    """Test chat_stream method in RAGPipeline."""
    from app.pipeline import RAGPipeline

    # Mock dependencies
    with patch("app.pipeline.OpenAIClient"):
        mock_stream = MagicMock()
        mock_stream.chat_stream.return_value = iter(["Hello", " ", "world", "!"])

        pipeline = RAGPipeline()
        pipeline.llm = mock_stream

        # Mock other dependencies
        pipeline.metadata_store = AsyncMock()
        pipeline.metadata_store.get_session.return_value = None
        pipeline.metadata_store.create_session.return_value = MagicMock(
            id="test_session", message_count=0
        )
        pipeline.search = MagicMock(return_value=[])

        # Collect events
        events = []
        async for event in pipeline.chat_stream(
            message="Test message",
            user_id="test_user",
            model="gpt-4o-mini",
        ):
            events.append(event)

        # Verify events
        assert len(events) >= 3  # metadata, content chunks, done
        assert events[0]["type"] == "metadata"
        assert "session_id" in events[0]
        assert any(e["type"] == "content" for e in events)
        assert events[-1]["type"] == "done"
        assert "tokens_used" in events[-1]


def test_chat_stream_endpoint_integration(client: TestClient):
    """Test /chat/stream endpoint (integration test - requires running server)."""
    # Note: This test requires a real OpenAI API key and running backend
    # Skip in CI/CD unless API key is available
    import os

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    response = client.post(
        "/chat/stream",
        json={
            "message": "What is RAG?",
            "user_id": "test_user",
            "model": "gpt-4o-mini",
            "top_k": 1,
        },
        stream=True,
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

    # Parse SSE events
    events = []
    for line in response.iter_lines():
        if line.startswith(b"data: "):
            try:
                data = json.loads(line[6:].decode("utf-8"))
                events.append(data)
            except json.JSONDecodeError:
                pass

    # Verify event structure
    assert len(events) > 0
    assert any(e.get("type") == "metadata" for e in events)
    assert any(e.get("type") == "content" for e in events)
    assert any(e.get("type") == "done" for e in events)


def test_chat_stream_error_handling(client: TestClient):
    """Test error handling in streaming endpoint."""
    # Send invalid request
    response = client.post(
        "/chat/stream",
        json={
            "message": "",  # Empty message should fail
            "user_id": "test_user",
        },
        stream=True,
    )

    # Should still return 200 for SSE, but with error event
    assert response.status_code in [200, 422]  # 422 for validation error


@pytest.mark.unit
def test_streaming_models():
    """Test Pydantic streaming event models."""
    from app.models import (
        ContentEvent,
        DoneEvent,
        ErrorEvent,
        MetadataEvent,
    )

    # Test MetadataEvent
    metadata = MetadataEvent(
        session_id="test_123",
        sources=[],
    )
    assert metadata.type == "metadata"
    assert metadata.session_id == "test_123"

    # Test ContentEvent
    content = ContentEvent(delta="Hello")
    assert content.type == "content"
    assert content.delta == "Hello"

    # Test DoneEvent
    done = DoneEvent(
        tokens_used=100,
        cost_usd=0.001,
        processing_time_ms=1234.5,
    )
    assert done.type == "done"
    assert done.tokens_used == 100

    # Test ErrorEvent
    error = ErrorEvent(message="Something went wrong")
    assert error.type == "error"
    assert error.message == "Something went wrong"
