"""Tests for MetadataStore operations."""

import pytest

from gundy_ai.metadata_store import MetadataStore


@pytest.fixture
async def store():
    """Create in-memory SQLite store."""
    store = MetadataStore("sqlite+aiosqlite:///:memory:", async_mode=True)
    await store.initialize()
    return store


@pytest.mark.asyncio
async def test_create_session(store):
    """Test creating a session."""
    session = await store.create_session(user_id="user123", metadata={"client": "web"})

    assert session.id.startswith("session_")
    assert session.user_id == "user123"
    assert session.message_count == 0
    assert session.metadata_json == {"client": "web"}


@pytest.mark.asyncio
async def test_get_session(store):
    """Test retrieving a session."""
    created = await store.create_session(user_id="user123")

    retrieved = await store.get_session(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.user_id == created.user_id


@pytest.mark.asyncio
async def test_get_nonexistent_session(store):
    """Test retrieving non-existent session returns None."""
    session = await store.get_session("nonexistent")

    assert session is None


@pytest.mark.asyncio
async def test_list_user_sessions(store):
    """Test listing sessions for a user."""
    # Create multiple sessions
    await store.create_session(user_id="user123")
    await store.create_session(user_id="user123")
    await store.create_session(user_id="user456")

    # List sessions for user123
    sessions = await store.list_user_sessions(user_id="user123")

    assert len(sessions) == 2
    assert all(s.user_id == "user123" for s in sessions)


@pytest.mark.asyncio
async def test_add_message(store):
    """Test adding a message to a session."""
    session = await store.create_session(user_id="user123")

    message = await store.add_message(
        session_id=session.id,
        role="user",
        content="Hello!",
    )

    assert message.id.startswith("msg_")
    assert message.session_id == session.id
    assert message.role == "user"
    assert message.content == "Hello!"


@pytest.mark.asyncio
async def test_add_message_with_metadata(store):
    """Test adding message with full metadata."""
    session = await store.create_session(user_id="user123")

    message = await store.add_message(
        session_id=session.id,
        role="assistant",
        content="Hello there!",
        model="gpt-4o-mini",
        tokens_used=50,
        cost_usd=0.00005,
        sources={"chunks": ["chunk_1", "chunk_2"]},
    )

    assert message.model == "gpt-4o-mini"
    assert message.tokens_used == 50
    assert message.cost_usd == 0.00005
    assert message.sources_json == {"chunks": ["chunk_1", "chunk_2"]}


@pytest.mark.asyncio
async def test_add_message_updates_session_count(store):
    """Test that adding message updates session message count."""
    session = await store.create_session(user_id="user123")
    assert session.message_count == 0

    await store.add_message(session.id, "user", "Message 1")
    await store.add_message(session.id, "assistant", "Message 2")

    # Retrieve session again
    updated_session = await store.get_session(session.id)

    assert updated_session.message_count == 2


@pytest.mark.asyncio
async def test_get_conversation_history(store):
    """Test retrieving conversation history."""
    session = await store.create_session(user_id="user123")

    # Add messages
    await store.add_message(session.id, "user", "Hello")
    await store.add_message(session.id, "assistant", "Hi there")
    await store.add_message(session.id, "user", "How are you?")

    # Get history
    history = await store.get_conversation_history(session.id)

    assert len(history) == 3
    assert history[0].role == "user"
    assert history[1].role == "assistant"
    assert history[2].role == "user"


@pytest.mark.asyncio
async def test_get_conversation_history_with_limit(store):
    """Test pagination of conversation history."""
    session = await store.create_session(user_id="user123")

    # Add 5 messages
    for i in range(5):
        await store.add_message(session.id, "user", f"Message {i}")

    # Get limited history
    history = await store.get_conversation_history(session.id, limit=3)

    assert len(history) == 3


@pytest.mark.asyncio
async def test_create_document(store):
    """Test creating a document with chunk mappings."""
    doc = await store.create_document(
        name="test.pdf",
        user_id="user123",
        chunks=["chunk_1", "chunk_2", "chunk_3"],
        status="completed",
        file_size=1024,
        file_type=".pdf",
        metadata={"source": "upload"},
    )

    assert doc.id.startswith("doc_")
    assert doc.name == "test.pdf"
    assert doc.user_id == "user123"
    assert doc.chunks_count == 3
    assert doc.status == "completed"


@pytest.mark.asyncio
async def test_get_document(store):
    """Test retrieving a document."""
    created = await store.create_document(
        name="test.txt", user_id="user123", chunks=["chunk_1"]
    )

    retrieved = await store.get_document(created.id)

    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == created.name


@pytest.mark.asyncio
async def test_list_user_documents(store):
    """Test listing documents for a user."""
    await store.create_document("doc1.pdf", "user123", ["chunk_1"])
    await store.create_document("doc2.pdf", "user123", ["chunk_2"])
    await store.create_document("doc3.pdf", "user456", ["chunk_3"])

    docs = await store.list_user_documents("user123")

    assert len(docs) == 2
    assert all(d.user_id == "user123" for d in docs)


@pytest.mark.asyncio
async def test_get_document_chunks(store):
    """Test retrieving chunk IDs for a document."""
    doc = await store.create_document(
        name="test.pdf",
        user_id="user123",
        chunks=["chunk_1", "chunk_2", "chunk_3"],
    )

    chunk_ids = await store.get_document_chunks(doc.id)

    assert len(chunk_ids) == 3
    assert chunk_ids == ["chunk_1", "chunk_2", "chunk_3"]


@pytest.mark.asyncio
async def test_delete_document(store):
    """Test deleting a document returns chunk IDs."""
    doc = await store.create_document(
        name="test.pdf",
        user_id="user123",
        chunks=["chunk_1", "chunk_2", "chunk_3"],
    )

    # Delete document
    chunk_ids = await store.delete_document(doc.id)

    assert len(chunk_ids) == 3
    assert set(chunk_ids) == {"chunk_1", "chunk_2", "chunk_3"}

    # Document should be deleted
    retrieved = await store.get_document(doc.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_user_stats(store):
    """Test getting user statistics."""
    # Create sessions and documents
    session1 = await store.create_session(user_id="user123")
    await store.create_session(user_id="user123")

    await store.add_message(session1.id, "user", "Hello")
    await store.add_message(session1.id, "assistant", "Hi")

    await store.create_document("doc1.pdf", "user123", ["chunk_1"])
    await store.create_document("doc2.pdf", "user123", ["chunk_2"])

    # Get stats
    stats = await store.get_user_stats("user123")

    assert stats["user_id"] == "user123"
    assert stats["sessions"] == 2
    assert stats["documents"] == 2
    assert stats["total_messages"] == 2
