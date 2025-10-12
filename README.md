# ai-utils

**Stable, well-tested utilities and libraries for building production-ready AI applications.**

## Philosophy

ai-utils provides **core building blocks** for AI applications:

- ✅ Reusable libraries (`libs/`) - extractors, chunkers, embeddings, vector stores
- ✅ Generic infrastructure services (`services/`) - auth, basic RAG API
- ✅ Templates (`templates/`) - starting points for common patterns

ai-utils does **NOT** include:

- ❌ Complete end-user applications
- ❌ Use-case specific business logic
- ❌ Opinionated product features

> For complete implementations that use these libraries, see:
>
> - [portfolio-chatbot](../portfolio-chatbot) - Lead generation chatbot example
> - [templates/rag-starter](./templates/rag-starter) - Starting point for RAG apps

## Quick Start

### Using as Libraries

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-utils.git
cd ai-utils

# Install a specific library
cd libs/extractors
poetry install

# Or reference in your project's pyproject.toml
```

```toml
[tool.poetry.dependencies]
# Local development
gundy-ai-extractors = {path = "../ai-utils/libs/extractors", develop = true}

# Or when published to PyPI:
gundy-ai-extractors = ">=0.1,<1.0"
```

### Using Templates

```bash
# Copy a template to start your project
cp -r templates/rag-starter my-rag-app
cd my-rag-app

# Follow the template's README
```

## Repository Structure

```
ai-utils/
├── libs/                      # Core reusable libraries
│   ├── extractors/           # Document parsing (TXT, PDF, DOCX)
│   ├── chunker/              # Token-aware text chunking
│   ├── embeddings/           # Embedding providers (OpenAI, etc.)
│   ├── vectorstore/          # Vector database adapters (ChromaDB, FAISS)
│   ├── metadata-store/       # Session/document/lead metadata
│   ├── job-queue/            # Background job processing
│   └── llm_wrappers/         # LLM client wrappers
├── services/                  # Generic infrastructure services
│   ├── auth-secrets-service/ # Authentication and secrets management
│   └── rag-api/              # Basic RAG API service
├── templates/                 # Starter templates
│   ├── rag-starter/          # RAG chatbot template
│   ├── api-service-starter/  # FastAPI service template
│   └── webapp-starter/       # Next.js webapp template
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md       # Architecture philosophy
│   ├── versioning.md         # Version management
│   └── ...                   # Component-specific docs
└── .cursorrules              # Development guidelines
```

## Core Libraries

### 1. Extractors (`libs/extractors`)

Document parsing plugin system.

```python
from gundy_ai.extractors import ParserRegistry

registry = ParserRegistry()
text = registry.parse("document.pdf")
```

**Supported formats:** TXT, PDF, DOCX, Markdown, CSV, Logs

### 2. Chunker (`libs/chunker`)

Token-aware text chunking.

```python
from gundy_ai.chunker import TokenAwareChunker

chunker = TokenAwareChunker(max_tokens=512, overlap_tokens=50)
chunks = chunker.chunk(text)
```

### 3. Embeddings (`libs/embeddings`)

Provider-agnostic embedding generation.

```python
from gundy_ai.embeddings import OpenAIEmbeddingProvider

provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")
embeddings = await provider.embed_texts(["Hello, world!"])
```

### 4. Vector Store (`libs/vectorstore`)

Extensible vector database adapters.

```python
from gundy_ai.vectorstore import ChromaDBAdapter

store = ChromaDBAdapter(persist_directory="./vector_db")
await store.upsert(ids=["1"], embeddings=[[...]], texts=["..."])
results = await store.search(query_embedding=[...], top_k=5)
```

**Supported:** ChromaDB, FAISS (more coming)

### 5. Metadata Store (`libs/metadata-store`)

Persistent session and document metadata.

```python
from gundy_ai.metadata_store import MetadataStore

store = MetadataStore("sqlite+aiosqlite:///metadata.db")
await store.create_session(session_id="123")
await store.add_message(session_id="123", role="user", content="Hi")
```

**Features:** Sessions, messages, documents, leads, audit logging

### 6. Job Queue (`libs/job-queue`)

Background job processing.

```python
from gundy_ai.job_queue import InMemoryQueue

queue = InMemoryQueue()
job = await queue.enqueue(job_type="ingest", payload={...})
```

**Backends:** In-memory, Redis

## Services

### RAG API (`services/rag-api`)

Production-ready RAG API that integrates all libraries.

```bash
cd services/rag-api
cp env.example .env
# Add OPENAI_API_KEY to .env
poetry install
poetry run uvicorn app.main:app --reload
```

**Endpoints:**

- `POST /documents/ingest` - Upload and process documents
- `POST /chat` - RAG-powered chat
- `POST /search` - Semantic search
- `GET /stats` - System statistics

### Auth & Secrets Service (`services/auth-secrets-service`)

Authentication, RBAC, and secrets management.

See [docs/auth-secrets-service.md](docs/auth-secrets-service.md) for details.

## Templates

### RAG Starter (`templates/rag-starter`)

Full-stack RAG chatbot with Next.js frontend and FastAPI backend.

**Includes:**

- Document upload and management
- Chat interface with conversation history
- Source attribution and citations
- System configuration UI
- Health monitoring

**Quick start:**

```bash
cp -r templates/rag-starter my-chatbot
cd my-chatbot
# Follow README.md
```

## Development Guidelines

See [`.cursorrules`](.cursorrules) for comprehensive development guidelines including:

- **API-first design** - Always spec before implementing
- **Security by default** - RBAC, secrets management, audit logging
- **Versioning** - Semantic versioning and dependency management
- **Testing** - Unit tests, integration tests, contract tests
- **Documentation** - Keep READMEs up-to-date

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - Architecture philosophy and library ecosystem
- [`docs/versioning.md`](docs/versioning.md) - Version management guidelines
- [`docs/key-components.md`](docs/key-components.md) - Component status and roadmap
- Individual library READMEs in `libs/*/README.md`

## Examples

Each library includes examples in `libs/*/examples/`:

```bash
cd libs/extractors
python examples/basic_usage.py
```

## Testing

```bash
# Test all libraries
./scripts/test-all.sh

# Test specific library
cd libs/extractors
poetry run pytest
```

## Contributing

1. Follow the guidelines in `.cursorrules`
2. Keep changes focused on core, reusable functionality
3. Add tests for new features
4. Update documentation
5. Use semantic versioning for releases

## Use Cases

ai-utils powers:

- **RAG chatbots** - Document Q&A, knowledge bases
- **Semantic search** - Content discovery, recommendations
- **Document processing pipelines** - ETL, data extraction
- **AI agents** - Tool-calling, multi-step reasoning

## Roadmap

See [`docs/key-components.md`](docs/key-components.md) for detailed component status.

**P0 (MVP):**

- ✅ Extractors / Parsers
- ✅ Chunker
- ✅ Embedding Service
- ✅ Vector Store Adapter
- ✅ Metadata Store
- ✅ Job Queue
- ✅ API Gateway

**P1 (Production):**

- ✅ Auth & RBAC
- ✅ Audit Logging
- ✅ Secrets Manager
- 🔨 Rate Limiter
- 🔨 CI/CD & Tests

**P2+ (Advanced):**

- Multi-modal embeddings
- More vector stores (Pinecone, Weaviate)
- More LLM providers (Anthropic, local models)
- Feature flags
- Advanced observability

## License

MIT License - See LICENSE file for details.
