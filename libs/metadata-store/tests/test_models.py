"""Tests for SQLAlchemy models."""

from gundy_ai.metadata_store import Document, DocumentChunk, Message, Session


def test_session_model():
    """Test Session model creation."""
    session = Session(
        id="session_123",
        user_id="user_456",
        message_count=5,
        metadata_json={"preference": "dark_mode"},
    )

    assert session.id == "session_123"
    assert session.user_id == "user_456"
    assert session.message_count == 5
    assert session.metadata_json == {"preference": "dark_mode"}


def test_message_model():
    """Test Message model creation."""
    message = Message(
        id="msg_789",
        session_id="session_123",
        role="user",
        content="Hello!",
        model="gpt-4o-mini",
        tokens_used=10,
        cost_usd=0.00001,
    )

    assert message.id == "msg_789"
    assert message.session_id == "session_123"
    assert message.role == "user"
    assert message.content == "Hello!"
    assert message.tokens_used == 10


def test_document_model():
    """Test Document model creation."""
    document = Document(
        id="doc_abc",
        name="test.pdf",
        user_id="user_456",
        status="completed",
        chunks_count=10,
        file_size=1024,
        file_type=".pdf",
    )

    assert document.id == "doc_abc"
    assert document.name == "test.pdf"
    assert document.user_id == "user_456"
    assert document.status == "completed"
    assert document.chunks_count == 10


def test_document_chunk_model():
    """Test DocumentChunk model creation."""
    chunk = DocumentChunk(document_id="doc_abc", chunk_id="chunk_1", chunk_index=0)

    assert chunk.document_id == "doc_abc"
    assert chunk.chunk_id == "chunk_1"
    assert chunk.chunk_index == 0
