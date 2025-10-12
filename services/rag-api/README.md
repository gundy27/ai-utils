# RAG API Service

Production-ready RAG (Retrieval-Augmented Generation) API service that integrates all gundy-ai libraries into a complete document processing and search system.

## Features

- **Complete RAG Pipeline**: Extract → Chunk → Embed → Store → Query
- **Multiple File Types**: TXT, PDF, DOCX support
- **Semantic Search**: Natural language document queries
- **Health Monitoring**: Check all pipeline components
- **Audit Logging**: Track all operations with structlog
- **OpenAPI Documentation**: Interactive API docs
- **Type-Safe**: Full Pydantic validation
- **CORS Ready**: Frontend integration support

## Architecture

```
Document Upload → Parser (TXT/PDF/DOCX) → Chunker (Token-aware)
    → Embeddings (OpenAI) → Vector Store (ChromaDB) → Search Results
```

**Libraries Used**:

- `gundy-ai-extractors`: Document parsing
- `gundy-ai-chunker`: Text chunking
- `gundy-ai-embeddings`: Vector generation
- `gundy-ai-vectorstore`: Storage & retrieval

## Quick Start

```bash
# 1. Install dependencies
cd services/rag-api
poetry install

# 2. Set environment variables
cp env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Run server
poetry run uvicorn app.main:app --reload --port 8000

# 4. Visit API docs
open http://localhost:8000/docs
```

## API Endpoints

### Chat

**POST `/chat`**
Chat with your documents using RAG.

Request:

```json
{
  "message": "What is machine learning?",
  "session_id": "session_abc123",
  "user_id": "user123",
  "top_k": 5,
  "model": "gpt-4o-mini",
  "include_sources": true
}
```

Response:

```json
{
  "answer": "Machine learning is a subset of AI that...",
  "session_id": "session_abc123",
  "sources": [
    {
      "chunk_id": "doc_abc123_chunk_0",
      "score": 0.95,
      "text": "Machine learning is..."
    }
  ],
  "model": "gpt-4o-mini",
  "tokens_used": 250,
  "cost_usd": 0.00025,
  "processing_time_ms": 850.5
}
```

**POST `/chat/stream`** 🆕 Streaming
Stream chat responses with real-time updates using Server-Sent Events (SSE).

Request (same as `/chat`):

```json
{
  "message": "Explain quantum computing",
  "session_id": "session_abc123",
  "user_id": "user123",
  "top_k": 5,
  "model": "gpt-4o-mini"
}
```

Response: Server-Sent Events stream

```
data: {"type":"metadata","session_id":"session_abc123","sources":[{"chunk_id":"doc_xyz","score":0.92}]}

data: {"type":"content","delta":"Quantum"}

data: {"type":"content","delta":" computing"}

data: {"type":"content","delta":" is..."}

data: {"type":"done","tokens_used":300,"cost_usd":0.0003,"processing_time_ms":1200.5}
```

**Event Types**:

- `metadata`: Session ID and retrieved source chunks
- `content`: Text delta to append to response
- `done`: Final statistics (tokens, cost, time)
- `error`: Error message if something fails

**Example with curl**:

```bash
curl -N http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "test"}'
```

**Benefits**:

- ✅ Better UX - users see responses as they're generated
- ✅ Progressive disclosure - start reading before completion
- ✅ Perceived performance - feels faster
- ✅ Real-time feedback - see progress immediately

### Document Management

**POST `/documents/ingest`**
Upload and process a document through the RAG pipeline.

Request (multipart/form-data):

```bash
curl -X POST "http://localhost:8000/documents/ingest" \
  -F "file=@document.pdf" \
  -F 'metadata={"source": "upload"}'
```

Response:

```json
{
  "document_id": "doc_abc123",
  "chunks_created": 15,
  "vectors_stored": 15,
  "total_tokens": 2048,
  "estimated_cost_usd": 0.00004,
  "processing_time_ms": 1250.5
}
```

**POST `/search`**
Search for similar documents using semantic similarity.

Request:

```json
{
  "query": "What is machine learning?",
  "top_k": 5,
  "filter": { "source": "upload" },
  "include_text": true
}
```

Response:

```json
{
  "query": "What is machine learning?",
  "results": [
    {
      "chunk_id": "doc_abc123_chunk_0",
      "document_id": "doc_abc123",
      "score": 0.95,
      "text": "Machine learning is...",
      "metadata": { "document_name": "ml_intro.pdf" }
    }
  ],
  "total_results": 5,
  "processing_time_ms": 150.2
}
```

### Monitoring

**GET `/health`**
Check health of all pipeline components.

**GET `/stats`**
Get pipeline statistics (vector count, model info, etc.).

**GET `/`**
API information and links.

## Using the Client

The included example client makes it easy to interact with the API:

```bash
# Check health
poetry run python examples/client.py

# Ingest a document
poetry run python examples/client.py path/to/document.pdf

# Ingest and search
poetry run python examples/client.py document.pdf "What is this about?"
```

## Configuration

Environment variables (see `env.example`):

| Variable               | Default                  | Description              |
| ---------------------- | ------------------------ | ------------------------ |
| `OPENAI_API_KEY`       | (required)               | OpenAI API key           |
| `VECTOR_DB_PATH`       | `./vector_db`            | Vector database path     |
| `COLLECTION_NAME`      | `documents`              | ChromaDB collection name |
| `CHUNK_MAX_TOKENS`     | `512`                    | Maximum tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | `50`                     | Overlap between chunks   |
| `EMBEDDING_MODEL`      | `text-embedding-3-small` | OpenAI embedding model   |
| `METADATA_DB_URL`      | `sqlite+aiosqlite:...`   | Metadata database URL    |
| `DEFAULT_CHAT_MODEL`   | `gpt-4o-mini`            | Default LLM for chat     |

## Testing

```bash
# Run tests (basic tests don't require API key)
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Test with API key (integration tests)
export OPENAI_API_KEY="your-key"
poetry run pytest tests/test_api.py::test_ingest_and_search
```

## Development

```bash
# Run with auto-reload
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run in Docker
docker build -t rag-api .
docker run -p 8000:8000 -e OPENAI_API_KEY="your-key" rag-api
```

## Production Deployment

For production:

1. **Set proper CORS origins** in config
2. **Add authentication** (JWT, OAuth2, etc.)
3. **Add rate limiting** (per user, per endpoint)
4. **Monitor health checks** (integrate with monitoring tools)
5. **Scale workers** (multiple uvicorn workers)
6. **Add document index** (track document→chunks mapping)
7. **Implement proper document deletion** (with document index)

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Example Workflow

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# 1. Upload document
with open("document.pdf", "rb") as f:
    response = client.post(
        "/documents/ingest",
        files={"file": f},
        data={"metadata": '{"source": "test"}'}
    )
    doc_id = response.json()["document_id"]

# 2. Chat with your documents
response = client.post(
    "/chat",
    json={
        "message": "What is the main topic?",
        "user_id": "user123",
        "top_k": 5
    }
)
chat_data = response.json()
print(f"Answer: {chat_data['answer']}")
print(f"Session: {chat_data['session_id']}")
print(f"Cost: ${chat_data['cost_usd']:.6f}")

# 3. Continue conversation (with history)
response = client.post(
    "/chat",
    json={
        "message": "Tell me more about that",
        "session_id": chat_data['session_id'],  # Same session
        "user_id": "user123"
    }
)

# 4. Search (alternative to chat)
response = client.post(
    "/search",
    json={"query": "What is the main topic?", "top_k": 3}
)
results = response.json()["results"]
```

## Limitations & Future Improvements

**Current Limitations**:

- Document deletion is incomplete (needs document→chunks index)
- No document listing (needs separate document table)
- No user authentication
- No rate limiting
- In-memory session state (use Redis for production)

**Future Improvements**:

- Add more extractors (HTML, Excel, Images with OCR)
- Support async processing for large files
- Add caching layer (Redis)
- Implement full document lifecycle management
- Add vector database migration tools
- Support multiple vector stores (FAISS, Pinecone)

## Requirements

- Python >=3.11,<3.13
- OpenAI API key for embeddings
- All gundy-ai libraries (extractors, chunker, embeddings, vectorstore)

## License

See main ai-utils repository.

## Contributing

Follow the project guidelines in `.cursorrules` at repository root.
