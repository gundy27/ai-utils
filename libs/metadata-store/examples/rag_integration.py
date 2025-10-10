"""Example showing metadata store integration with RAG pipeline."""

import asyncio
import os
import tempfile
from pathlib import Path

# Check if all dependencies available
try:
    from gundy_ai.extractors import ParserRegistry, TXTParser
    from gundy_ai.chunker import TokenAwareChunker
    from gundy_ai.embeddings import OpenAIEmbeddingProvider
    from gundy_ai.vectorstore import ChromaDBAdapter

    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False
    print("Note: This example requires all gundy-ai libraries")
    print("Proceeding with metadata store demo only...")

from gundy_ai.metadata_store import MetadataStore


async def full_rag_with_metadata():
    """Demonstrate complete RAG with metadata tracking."""

    print("=== Complete RAG with Metadata Tracking ===\n")

    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        return

    # Sample document
    document_text = """
    Metadata stores are essential for tracking chat sessions and document lifecycle.
    They enable features like conversation history, user preferences, and proper
    document deletion that includes removing all associated vector embeddings.

    A good metadata store should track:
    - Chat sessions with user IDs and timestamps
    - Message history with costs and token usage
    - Document metadata with chunk mappings
    - User statistics and analytics
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(document_text)
        doc_path = f.name

    vector_db_dir = tempfile.mkdtemp()
    metadata_db = tempfile.mktemp(suffix=".db")

    try:
        # Initialize all components
        print("Initializing components...")

        # Metadata store
        metadata_store = MetadataStore(f"sqlite+aiosqlite:///{metadata_db}")
        await metadata_store.initialize()

        # RAG pipeline
        registry = ParserRegistry()
        registry.register(TXTParser())
        chunker = TokenAwareChunker(max_tokens=100, overlap_tokens=20)
        embeddings = OpenAIEmbeddingProvider()
        vectorstore = ChromaDBAdapter(persist_directory=vector_db_dir)

        print("✓ All components ready\n")

        # Create a user session
        print("Step 1: Create User Session")
        print("-" * 70)

        session = await metadata_store.create_session(
            user_id="demo_user", metadata={"source": "cli_demo"}
        )

        print(f"Session: {session.id}")
        print(f"User: {session.user_id}\n")

        # Process document
        print("Step 2: Process Document")
        print("-" * 70)

        # Extract
        extracted = registry.get_parser(".txt").parse(doc_path)
        chunks = chunker.chunk(extracted[0].text)
        chunk_texts = [chunk.text for chunk in chunks]

        # Embed
        embedding_result = embeddings.embed(chunk_texts)

        # Store in vectorstore
        chunk_ids = [f"chunk_{i}" for i in range(len(chunks))]
        chunk_metadatas = [{"chunk_index": i} for i in range(len(chunks))]

        vectorstore.upsert(
            ids=chunk_ids,
            embeddings=embedding_result.embeddings,
            metadatas=chunk_metadatas,
            texts=chunk_texts,
        )

        # Track in metadata store
        document = await metadata_store.create_document(
            name="metadata_guide.txt",
            user_id="demo_user",
            chunks=chunk_ids,
            status="completed",
            file_size=len(document_text),
            file_type=".txt",
            metadata={"category": "documentation"},
        )

        print(f"Document: {document.id}")
        print(f"Chunks: {len(chunk_ids)}")
        print(f"Cost: ${embedding_result.estimated_cost_usd:.6f}\n")

        # Chat interaction
        print("Step 3: Chat Interaction")
        print("-" * 70)

        # User asks question
        user_query = "What should a metadata store track?"

        await metadata_store.add_message(
            session_id=session.id, role="user", content=user_query
        )

        # Search for relevant chunks
        query_embedding = embeddings.embed([user_query]).embeddings[0]
        search_results = vectorstore.query(query_embedding=query_embedding, top_k=2)

        # Simulate LLM response (in real app, use OpenAIClient)
        assistant_response = f"Based on the documents, a metadata store should track: {search_results[0].text[:100]}..."

        await metadata_store.add_message(
            session_id=session.id,
            role="assistant",
            content=assistant_response,
            model="gpt-4o-mini",
            tokens_used=75,
            cost_usd=0.000075,
            sources={"chunks": [r.id for r in search_results]},
        )

        print(f"User: {user_query}")
        print(f"Assistant: {assistant_response[:100]}...\n")

        # Show conversation history
        print("Step 4: Conversation History")
        print("-" * 70)

        history = await metadata_store.get_conversation_history(session.id)

        for msg in history:
            role_emoji = "👤" if msg.role == "user" else "🤖"
            print(f"{role_emoji} [{msg.role}]: {msg.content[:60]}...")

        print()

        # Show user stats
        print("Step 5: User Statistics")
        print("-" * 70)

        stats = await metadata_store.get_user_stats("demo_user")

        print(f"Sessions: {stats['sessions']}")
        print(f"Documents: {stats['documents']}")
        print(f"Total messages: {stats['total_messages']}\n")

        # Delete document (including from vectorstore!)
        print("Step 6: Delete Document")
        print("-" * 70)

        chunk_ids_to_delete = await metadata_store.delete_document(document.id)

        print(f"Document {document.id} deleted")
        print(f"Deleting {len(chunk_ids_to_delete)} chunks from vectorstore...")

        vectorstore.delete(chunk_ids_to_delete)

        print("✓ Complete deletion (metadata + vectors)\n")

        # Summary
        print("=" * 70)
        print("\nComplete RAG with Metadata Tracking:")
        print("  ✓ Session management with user tracking")
        print("  ✓ Conversation history with costs")
        print("  ✓ Document lifecycle management")
        print("  ✓ Proper deletion (metadata + vectors)")
        print("  ✓ User statistics and analytics")
        print("\n🎉 Ready for production RAG chatbot!")

    finally:
        Path(doc_path).unlink(missing_ok=True)
        Path(metadata_db).unlink(missing_ok=True)
        import shutil

        shutil.rmtree(vector_db_dir, ignore_errors=True)


async def metadata_only_demo():
    """Demo with just metadata store (no RAG pipeline)."""
    print("=== Metadata Store Demo ===\n")

    metadata_db = tempfile.mktemp(suffix=".db")

    try:
        store = MetadataStore(f"sqlite+aiosqlite:///{metadata_db}")
        await store.initialize()

        # Create session
        session = await store.create_session("demo_user")
        print(f"Created session: {session.id}")

        # Add messages
        await store.add_message(session.id, "user", "Hello!")
        await store.add_message(session.id, "assistant", "Hi there!")

        # Get history
        history = await store.get_conversation_history(session.id)
        print(f"Messages: {len(history)}")

        # Create document
        doc = await store.create_document(
            name="test.txt", user_id="demo_user", chunks=["chunk_1", "chunk_2"]
        )
        print(f"Created document: {doc.id}")

        # Delete document
        chunk_ids = await store.delete_document(doc.id)
        print(f"Deleted document, chunk IDs: {chunk_ids}")

        print("\n✓ Complete!")

    finally:
        Path(metadata_db).unlink(missing_ok=True)


def main_entry():
    """Run appropriate demo based on what's available."""
    if DEPS_AVAILABLE:
        asyncio.run(full_rag_with_metadata())
    else:
        asyncio.run(metadata_only_demo())


if __name__ == "__main__":
    main_entry()
