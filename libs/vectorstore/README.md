# Gundy AI Vector Store

Extensible vector database adapters for AI applications with support for multiple providers.

## Features

- **Provider-Agnostic**: Unified interface for all vector databases
- **ChromaDB Integration**: Built-in support for ChromaDB with persistent storage
- **Extensible**: Easy to add Pinecone, Weaviate, Supabase, FAISS, etc.
- **Full CRUD**: Upsert, query, delete, count, clear operations
- **Metadata Filtering**: Query with metadata filters (ChromaDB where clauses)
- **Similarity Search**: Cosine, L2, and inner product distance metrics
- **Health Checks**: Verify database connectivity and get collection stats
- **Audit Logging**: Track all vector operations (embeddings redacted for security)
- **Type Safety**: Full Pydantic models with validation
- **Auto-persistence**: Changes automatically saved to disk

## Installation

```bash
# With ChromaDB support
poetry add gundy-ai-vectorstore[chromadb]

# Base installation (bring your own adapter)
poetry add gundy-ai-vectorstore
```

## Quick Start

```python
from gundy_ai.vectorstore import ChromaDBAdapter

# Create vector store
store = ChromaDBAdapter(
    persist_directory="./vector_db",
    collection_name="documents"
)

# Upsert vectors
store.upsert(
    ids=["doc1", "doc2"],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    metadatas=[{"title": "Doc 1"}, {"title": "Doc 2"}],
    texts=["Document 1 content", "Document 2 content"]
)

# Query similar vectors
results = store.query(
    query_embedding=[0.15, 0.25, ...],
    top_k=5
)

for result in results:
    print(f"{result.id}: {result.score:.3f}")
    print(f"  Text: {result.text}")
```

## Supported Adapters

### ChromaDB ✅

Local vector database with automatic persistence.

**Features**:

- Persistent storage to disk
- Cosine, L2, and inner product similarity
- Metadata filtering with where clauses
- Automatic collection management

```python
from gundy_ai.vectorstore import ChromaDBAdapter

store = ChromaDBAdapter(
    persist_directory="./vector_db",
    collection_name="documents",
    distance_metric="cosine"  # or "l2", "euclidean", "dot", "ip"
)
```

### Coming Soon 🔜

- **FAISS**: High-performance similarity search
- **Pinecone**: Managed cloud vector database
- **Supabase**: Postgres-based with pgvector
- **Weaviate**: GraphQL API with semantic search
- **Qdrant**: High-performance with advanced filtering

## Integration with Other Libraries

Works seamlessly with other gundy-ai libraries:

```python
from gundy_ai.extractors import ParserRegistry, PDFParser
from gundy_ai.chunker import TokenAwareChunker
from gundy_ai.embeddings import OpenAIEmbeddingProvider
from gundy_ai.vectorstore import ChromaDBAdapter

# 1. Extract text from PDF
registry = ParserRegistry()
registry.register(PDFParser())
extracted = registry.get_parser(".pdf").parse("document.pdf")

# 2. Chunk the text
chunker = TokenAwareChunker(max_tokens=512, overlap_tokens=50)
all_chunks = []
for page in extracted:
    chunks = chunker.chunk(page.text)
    all_chunks.extend(chunks)

# 3. Generate embeddings
provider = OpenAIEmbeddingProvider()
chunk_texts = [chunk.text for chunk in all_chunks]
embedding_result = provider.embed(chunk_texts)

# 4. Store in vector database
store = ChromaDBAdapter(persist_directory="./vector_db")
store.upsert(
    ids=[f"chunk_{i}" for i in range(len(all_chunks))],
    embeddings=embedding_result.embeddings,
    metadatas=[{"chunk_idx": i} for i in range(len(all_chunks))],
    texts=chunk_texts
)

# 5. Query for similar content
query = "What is the main topic?"
query_embedding = provider.embed([query]).embeddings[0]
results = store.query(query_embedding=query_embedding, top_k=5)
```

## API Reference

### ChromaDBAdapter

**Initialization**:

```python
store = ChromaDBAdapter(
    persist_directory="./vector_db",  # Directory for persistence
    collection_name="documents",       # Collection name
    distance_metric="cosine"           # Similarity metric
)
```

**Methods**:

**`upsert(ids, embeddings, metadatas=None, texts=None)`**

- Upsert vectors with metadata
- Updates existing vectors if IDs match
- `metadatas` must be non-empty dicts (auto-filled if empty)

**`query(query_embedding, top_k=10, filter=None, include_embeddings=False)`**

- Query for similar vectors
- Returns `List[QueryResult]` sorted by similarity
- `filter`: ChromaDB where clause (e.g., `{"category": "AI"}`)

**`delete(ids)`**

- Delete vectors by IDs
- Returns count of deleted vectors

**`count()`**

- Get total number of vectors

**`clear()`**

- Delete all vectors from collection

**`health_check()`**

- Check if vector store is accessible
- Returns health status with count and latency

**Properties**:

- `adapter_name`: "chromadb"
- `collection_name`: Collection name

### QueryResult

Result from similarity search:

```python
result = QueryResult(
    id="doc_123",
    score=0.95,                    # Higher = more similar
    metadata={"title": "Sample"},
    text="Sample document text",
    embedding=[0.1, 0.2, ...]     # If include_embeddings=True
)
```

### Models

**VectorDocument**: Document with embedding

- `id`: Unique identifier
- `embedding`: Vector
- `metadata`: Metadata dict
- `text`: Original text (optional)

**StoreConfig**: Configuration for vector store

- `adapter_name`: Adapter identifier
- `persist_directory`: Persistence path
- `collection_name`: Collection/index name
- `embedding_dimension`: Vector dimensions
- `distance_metric`: Distance metric

## Metadata Filtering

ChromaDB supports metadata filtering with where clauses:

```python
# Exact match
results = store.query(
    query_embedding=embedding,
    filter={"category": "AI"}
)

# Multiple conditions (AND)
results = store.query(
    query_embedding=embedding,
    filter={"category": "AI", "language": "en"}
)

# Operators
results = store.query(
    query_embedding=embedding,
    filter={"year": {"$gte": 2020}}  # year >= 2020
)
```

## Audit Logging

All vector operations emit audit events:

- `vectorstore.upsert` - Vectors upserted
- `vectorstore.query` - Similarity search performed
- `vectorstore.delete` - Vectors deleted
- `vectorstore.health_check` - Health check performed

Events include:

- Adapter and collection
- Vector count and query parameters
- Latency and performance
- Outcome and errors
- **Note**: Embeddings are redacted from logs for security

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific adapter tests
poetry run pytest tests/adapters/test_chromadb.py
```

**Test Coverage**: 32 tests, 80% coverage

## Performance

ChromaDB performance (approximate):

- Upsert 100 vectors: ~50ms
- Query (top_k=10): ~20-50ms
- Scales to millions of vectors
- Uses HNSW index for fast similarity search

## Examples

See `examples/` directory:

- `basic_usage.py`: Simple vector store operations
- `full_pipeline.py`: Complete extraction → embedding → storage flow

## Distance Metrics

- **Cosine** (default): Best for normalized embeddings (OpenAI, Cohere)
- **L2/Euclidean**: Euclidean distance
- **Inner Product (IP/Dot)**: For non-normalized vectors

## Persistence

ChromaDB automatically persists to disk:

- Changes saved immediately
- Restart-safe
- Multi-process safe (use separate collections)

## Creating Custom Adapters

Implement `BaseVectorStore` interface:

```python
from gundy_ai.vectorstore import BaseVectorStore, QueryResult

class MyVectorStore(BaseVectorStore):
    def upsert(self, ids, embeddings, metadatas=None, texts=None):
        # Implementation
        pass

    def query(self, query_embedding, top_k=10, filter=None, include_embeddings=False):
        # Implementation
        return [QueryResult(...)]

    def delete(self, ids):
        # Implementation
        return len(ids)

    def count(self):
        # Implementation
        return total_count

    def health_check(self):
        return {"healthy": True, "adapter": "my_adapter", "collection": "..."}

    @property
    def adapter_name(self):
        return "my_adapter"

    @property
    def collection_name(self):
        return self._collection_name
```

## Requirements

- Python >=3.11,<3.13
- pydantic >=2.5,<3.0
- structlog >=23.2,<25.0
- chromadb >=0.4,<1.0 (for ChromaDB adapter)

## License

See main ai-utils repository.

## Contributing

Follow the project guidelines in `.cursorrules` at repository root.
