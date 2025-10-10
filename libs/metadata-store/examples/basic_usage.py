"""Basic usage example for gundy-ai-metadata-store."""

import asyncio

from gundy_ai.metadata_store import MetadataStore


async def main():
    """Demonstrate basic metadata store usage."""

    print("=== Gundy AI Metadata Store - Basic Usage ===\n")

    # Create store with SQLite
    store = MetadataStore("sqlite+aiosqlite:///./example_metadata.db")
    await store.initialize()

    print("✓ Store initialized\n")

    # 1. Create a session
    print("1. Creating chat session...")
    session = await store.create_session(
        user_id="user123", metadata={"client": "web", "preference": "dark_mode"}
    )

    print(f"   Session ID: {session.id}")
    print(f"   User: {session.user_id}")
    print(f"   Created: {session.created_at}\n")

    # 2. Add messages to conversation
    print("2. Adding messages...")

    await store.add_message(
        session_id=session.id, role="user", content="What is machine learning?"
    )

    await store.add_message(
        session_id=session.id,
        role="assistant",
        content="Machine learning is a subset of AI that learns from data...",
        model="gpt-4o-mini",
        tokens_used=150,
        cost_usd=0.00015,
        sources={"chunks": ["chunk_1", "chunk_2"]},
    )

    await store.add_message(
        session_id=session.id, role="user", content="Tell me more about neural networks"
    )

    await store.add_message(
        session_id=session.id,
        role="assistant",
        content="Neural networks are computational models inspired by the brain...",
        model="gpt-4o-mini",
        tokens_used=200,
        cost_usd=0.0002,
    )

    print("   ✓ Added 4 messages\n")

    # 3. Get conversation history
    print("3. Retrieving conversation history...")
    history = await store.get_conversation_history(session.id)

    for i, msg in enumerate(history):
        print(f"   {i + 1}. [{msg.role}]: {msg.content[:50]}...")
        if msg.tokens_used:
            print(f"      Tokens: {msg.tokens_used}, Cost: ${msg.cost_usd}")

    print()

    # 4. Create a document
    print("4. Creating document record...")
    doc = await store.create_document(
        name="ml_intro.pdf",
        user_id="user123",
        chunks=["chunk_1", "chunk_2", "chunk_3", "chunk_4"],
        status="completed",
        file_size=1024 * 512,  # 512KB
        file_type=".pdf",
        metadata={"source": "upload", "category": "AI"},
    )

    print(f"   Document ID: {doc.id}")
    print(f"   Name: {doc.name}")
    print(f"   Chunks: {doc.chunks_count}\n")

    # 5. List user's documents
    print("5. Listing user documents...")
    documents = await store.list_user_documents("user123")

    for i, document in enumerate(documents):
        print(f"   {i + 1}. {document.name} ({document.chunks_count} chunks)")

    print()

    # 6. Get document chunks
    print("6. Getting document chunks...")
    chunk_ids = await store.get_document_chunks(doc.id)

    print(f"   Chunk IDs: {chunk_ids}\n")

    # 7. Get user statistics
    print("7. User statistics...")
    stats = await store.get_user_stats("user123")

    print(f"   Sessions: {stats['sessions']}")
    print(f"   Documents: {stats['documents']}")
    print(f"   Total messages: {stats['total_messages']}\n")

    # 8. Delete document
    print("8. Deleting document...")
    deleted_chunk_ids = await store.delete_document(doc.id)

    print("   ✓ Document deleted")
    print(f"   Chunk IDs to delete from vectorstore: {deleted_chunk_ids}\n")

    print("✓ All operations complete!")


if __name__ == "__main__":
    from pathlib import Path

    # Cleanup old database
    db_path = Path("./example_metadata.db")
    if db_path.exists():
        db_path.unlink()

    asyncio.run(main())

    # Cleanup
    if db_path.exists():
        db_path.unlink()
