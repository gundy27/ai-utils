# Gundy AI Metadata Store

Persistent metadata and session management for RAG applications. Tracks chat sessions, conversation history, document metadata, and provides proper document lifecycle management.

## Features

- **Session Management**: Persistent chat sessions with user tracking
- **Conversation History**: Track all messages with cost and token usage
- **Document Lifecycle**: Full document tracking with chunk mapping
- **Proper Deletion**: Delete documents and get chunk IDs for vectorstore cleanup
- **SQLAlchemy ORM**: Type-safe async database operations
- **SQLite & Postgres**: Development and production databases
- **Audit Logging**: Track all operations (session.created, message.added, document.deleted)
- **User Analytics**: Get statistics per user
- **Type-Safe**: Full Pydantic models with validation

## Installation

```bash
# With SQLite support (development)
poetry add gundy-ai-metadata-store[sqlite]

# With Postgres support (production)
poetry add gundy-ai-metadata-store[postgres]

# With all drivers
poetry add gundy-ai-metadata-store[all]
```

## Quick Start

```python
from gundy_ai.metadata_store import MetadataStore

# Initialize store
store = MetadataStore("sqlite+aiosqlite:///./metadata.db")
await store.initialize()

# Create a session
session = await store.create_session(
    user_id="user123",
    metadata={"client": "web"}
)

# Add messages
await store.add_message(
    session_id=session.id,
    role="user",
    content="What is machine learning?",
)

await store.add_message(
    session_id=session.id,
    role="assistant",
    content="Machine learning is...",
    model="gpt-4o-mini",
    tokens_used=150,
    cost_usd=0.00015,
    sources={"chunks": ["chunk_1", "chunk_2"]}
)

# Get conversation history
history = await store.get_conversation_history(session.id, limit=10)

# Track document with chunk mapping
doc = await store.create_document(
    name="research.pdf",
    user_id="user123",
    chunks=["chunk_1", "chunk_2", "chunk_3"],
    status="completed",
    file_type=".pdf"
)

# Delete document (returns chunk IDs to delete from vectorstore!)
chunk_ids = await store.delete_document(doc.id)
# Then delete from vectorstore: vectorstore.delete(chunk_ids)
```

## Integration with RAG Pipeline

Complete example with all libraries:

```python
from gundy_ai.extractors import ParserRegistry, PDFParser
from gundy_ai.chunker import TokenAwareChunker
from gundy_ai.embeddings import OpenAIEmbeddingProvider
from gundy_ai.vectorstore import ChromaDBAdapter
from gundy_ai.metadata_store import MetadataStore

# Initialize
metadata_store = MetadataStore("sqlite+aiosqlite:///./metadata.db")
await metadata_store.initialize()

vectorstore = ChromaDBAdapter(persist_directory="./vector_db")
embeddings = OpenAIEmbeddingProvider()

# Create session
session = await metadata_store.create_session(user_id="user123")

# Process document
registry = ParserRegistry()
registry.register(PDFParser())
extracted = registry.get_parser(".pdf").parse("document.pdf")

chunker = TokenAwareChunker(max_tokens=512)
chunks = chunker.chunk(extracted[0].text)

# Embed and store
chunk_texts = [chunk.text for chunk in chunks]
embedding_result = embeddings.embed(chunk_texts)

chunk_ids = [f"doc_abc_chunk_{i}" for i in range(len(chunks))]
vectorstore.upsert(
    ids=chunk_ids,
    embeddings=embedding_result.embeddings,
    texts=chunk_texts
)

# Track in metadata store
document = await metadata_store.create_document(
    name="document.pdf",
    user_id="user123",
    chunks=chunk_ids,  # Maps document to vectorstore chunks!
    status="completed"
)

# Chat
await metadata_store.add_message(session.id, "user", "What is this about?")

query_embedding = embeddings.embed(["What is this about?"]).embeddings[0]
results = vectorstore.query(query_embedding=query_embedding, top_k=3)

# Use results with LLM (not shown)
await metadata_store.add_message(
    session.id,
    "assistant",
    "This document discusses...",
    model="gpt-4o-mini",
    sources={"chunks": [r.id for r in results]}
)

# Delete document properly!
chunk_ids_to_delete = await metadata_store.delete_document(document.id)
vectorstore.delete(chunk_ids_to_delete)  # Removes from vectorstore too!
```

## API Reference

### MetadataStore

**Initialization**:

```python
store = MetadataStore(
    database_url="sqlite+aiosqlite:///./metadata.db",
    async_mode=True,  # Default
    echo=False  # Set True for SQL logging
)
await store.initialize()  # Creates tables
```

**Database URLs**:

- SQLite: `sqlite+aiosqlite:///./metadata.db`
- Postgres: `postgresql+asyncpg://user:pass@localhost/dbname`

### Session Operations

**create_session(user_id, metadata=None)**

Create a new chat session.

**get_session(session_id)**

Retrieve session by ID.

**list_user_sessions(user_id, limit=50, offset=0)**

List sessions for a user, ordered by last activity.

### Message Operations

**add_message(session_id, role, content, model=None, tokens_used=None, cost_usd=None, sources=None, metadata=None)**

Add a message to a session. Automatically updates session message count and last activity.

**get_conversation_history(session_id, limit=50, offset=0)**

Get messages for a session, ordered by timestamp.

### Document Operations

**create_document(name, user_id, chunks, status="completed", file_size=None, file_type=None, metadata=None)**

Create document record with chunk mappings.

**get_document(document_id)**

Retrieve document by ID.

**list_user_documents(user_id, limit=50, offset=0)**

List documents for a user, ordered by upload time.

**get_document_chunks(document_id)**

Get all chunk IDs for a document (ordered by index).

**delete_document(document_id)**

Delete document and return chunk IDs that should be deleted from vectorstore.

**Important**: This is the key to proper cleanup! Use the returned chunk IDs to delete from your vector database.

### Analytics

**get_user_stats(user_id)**

Get statistics for a user (sessions, documents, total messages).

## Models

### Session

- `id`: Unique session identifier
- `user_id`: User identifier (for RBAC)
- `created_at`: Session creation time
- `last_activity`: Last interaction time (auto-updated)
- `message_count`: Number of messages (auto-incremented)
- `metadata_json`: Custom metadata dict

### Message

- `id`: Unique message identifier
- `session_id`: Parent session
- `role`: Message role (user, assistant, system)
- `content`: Message content
- `timestamp`: Message timestamp
- `model`: LLM model used (optional)
- `tokens_used`: Token count (optional)
- `cost_usd`: Cost in USD (optional)
- `sources_json`: Source chunks referenced (optional)
- `metadata_json`: Custom metadata (optional)

### Document

- `id`: Unique document identifier
- `name`: Document name
- `user_id`: Owner user ID
- `uploaded_at`: Upload timestamp
- `status`: processing, completed, or failed
- `chunks_count`: Number of chunks
- `file_size`: File size in bytes
- `file_type`: File extension
- `metadata_json`: Custom metadata

### DocumentChunk

- `document_id`: Parent document
- `chunk_id`: Chunk ID in vectorstore
- `chunk_index`: Chunk order

## Audit Logging

All operations emit audit events:

- `session.created` - New session created
- `session.accessed` - Session retrieved
- `message.added` - Message added to session
- `document.created` - Document created
- `document.deleted` - Document deleted

Events include:

- User ID, session ID, document ID
- Operation and outcome
- Timestamp and event ID

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Check specific operations
poetry run pytest tests/test_store.py::test_delete_document -v
```

**Test Coverage**: 19 tests, 95% coverage

## Examples

See `examples/` directory:

- `basic_usage.py`: Session, message, and document operations
- `rag_integration.py`: Complete RAG pipeline with metadata tracking

## Database Schema

```sql
-- Sessions
CREATE TABLE sessions (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    last_activity TIMESTAMP NOT NULL,
    message_count INTEGER NOT NULL DEFAULT 0,
    metadata JSON
);
CREATE INDEX ix_sessions_user_id ON sessions(user_id);
CREATE INDEX ix_sessions_last_activity ON sessions(last_activity);

-- Messages
CREATE TABLE messages (
    id VARCHAR(64) PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    model VARCHAR(100),
    tokens_used INTEGER,
    cost_usd FLOAT,
    sources JSON,
    metadata JSON
);
CREATE INDEX ix_messages_session_id ON messages(session_id);
CREATE INDEX ix_messages_timestamp ON messages(timestamp);

-- Documents
CREATE TABLE documents (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    user_id VARCHAR(255) NOT NULL,
    uploaded_at TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'processing',
    chunks_count INTEGER NOT NULL DEFAULT 0,
    file_size INTEGER,
    file_type VARCHAR(50),
    metadata JSON
);
CREATE INDEX ix_documents_user_id ON documents(user_id);
CREATE INDEX ix_documents_uploaded_at ON documents(uploaded_at);

-- Document-Chunk Mapping
CREATE TABLE document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id VARCHAR(64) NOT NULL,
    chunk_id VARCHAR(100) NOT NULL,
    chunk_index INTEGER NOT NULL
);
CREATE INDEX ix_doc_chunks_document ON document_chunks(document_id);
CREATE INDEX ix_doc_chunks_chunk_id ON document_chunks(chunk_id);
```

## Production Considerations

**For production deployments**:

1. **Use Postgres**: More robust than SQLite for multi-user scenarios

   ```python
   store = MetadataStore("postgresql+asyncpg://user:pass@localhost/ragdb")
   ```

2. **Add Indexes**: Already included for common query patterns

3. **Connection Pooling**: Configure SQLAlchemy pool size

   ```python
   engine = create_async_engine(
       database_url,
       pool_size=20,
       max_overflow=10
   )
   ```

4. **Data Retention**: Implement cleanup for old sessions

   ```sql
   DELETE FROM sessions WHERE last_activity < NOW() - INTERVAL '90 days';
   ```

5. **PII Redaction**: Apply redaction policies to message content if needed

6. **Backups**: Regular database backups for disaster recovery

## Requirements

- Python >=3.11,<3.13
- sqlalchemy >=2.0,<3.0
- pydantic >=2.5,<3.0
- structlog >=23.2,<25.0
- greenlet >=3.0,<4.0
- aiosqlite >=0.19,<1.0 (for SQLite)
- asyncpg >=0.29,<1.0 (for Postgres)

## License

See main ai-utils repository.

## Contributing

Follow the project guidelines in `.cursorrules` at repository root.
