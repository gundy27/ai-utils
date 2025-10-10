# Key Reusable Platform Components

Below are the minimum platform components you should build or verify exist before implementing a RAG template. Each entry includes responsibilities, a minimal API/contract, and audit/event hooks.

**Important**: Prefer small, well-tested adapters with explicit interfaces rather than monolithic libraries. Each adapter should be pinned to a stable contract (semantic versioned).

## Status Legend

- ✅ **Built**: Component exists and meets requirements
- 🔨 **Partial**: Component exists but needs enhancement
- ⏳ **Not Started**: Component needs to be built

## Priority Levels

- **P0 (Critical)**: Core RAG pipeline components - build first
- **P1 (High)**: Production readiness requirements
- **P2 (Medium)**: Important but can be deferred
- **P3 (Low)**: Future enhancements

## 2.1 Ingest Service (File Upload / API)

**Status**: 🔨 Partial | **Priority**: P1 (High)

**Responsibility**: Accept files (PDF, DOCX, TXT, CSV) and metadata; create a processing job; return job_id and status.

**Minimal API**:

- `POST /ingest` — multipart file + metadata -> `{ job_id, status: "queued" }`
- `GET /ingest/{job_id}` -> `{ status, progress, errors, artifacts: [...] }`

**Audit Hook**:

- Emit `audit.event` with `event_type: ingest.requested`
- Include `event_context: { user_id, file_name, size, upload_ip }`

**Current State**: Universal downloader exists (`libs/downloader/`) with HTTP/S3/FTP support but lacks job orchestration and REST API wrapper.

## 2.2 Extractors / Parsers (Plugin System)

**Status**: ⏳ Not Started | **Priority**: P0 (Critical)

**Responsibility**: Transform files to plain text and structured metadata.

**Contract**:

- Implement interface: `parse(file_path) -> [{ text, span_start, span_end, metadata }]`
- Plugin tip: Register plugin with manifest including `supported_types`, `version`, `schema`

**Audit Hook**:

- `audit.event` for `extractor.invoked`
- `extractor.succeeded` / `extractor.failed`

**Current State**: ✅ Fully implemented in `libs/extractors/` with:

- Plugin-based architecture with `BaseParser` interface
- **TXT Parser**: Supports .txt, .md, .csv, .log with multiple encodings
- **PDF Parser**: Extracts text page-by-page using pypdf
- **DOCX Parser**: Handles paragraphs and tables (with merged cell deduplication)
- Comprehensive audit logging for all operations
- 45 tests passing with 91% coverage
- Complete examples and documentation

## 2.3 Chunker (Token-aware)

**Status**: ✅ Built | **Priority**: P0 (Critical)

**Responsibility**: Convert extracted text into chunks with overlap, token-aware to avoid truncation.

**Contract**:

- `chunk(text, strategy={token_aware|fixed}, max_tokens, overlap) -> [chunks]`
- Each chunk has: `id`, `text`, `token_count`, `metadata`

**Guideline**: Prefer token-aware chunking by default; expose fixed-size for edge cases.

**Current State**: ✅ Fully implemented in `libs/chunker/` with:

- **TokenAwareChunker**: Respects LLM token limits using tiktoken (cl100k_base, p50k_base, r50k_base)
- **FixedSizeChunker**: Character-based chunking for simpler use cases
- Configurable overlap for maintaining context between chunks
- Comprehensive audit logging for all operations
- 38 tests passing with 93% coverage
- Performance: <1ms for small texts, ~50ms for 100K characters
- Complete examples and API documentation

## 2.4 Embedding Service (Provider-agnostic)

**Status**: ✅ Built | **Priority**: P0 (Critical)

**Responsibility**: Compute embeddings for chunks via provider adapter.

**Contract**:

- `embed(model, texts[]) -> [[float]]`
- Must include latency and cost metadata in response

**Adapter Requirements**:

- Implement `EmbeddingAdapter` with `health_check()` and retries/backoff
- Support OpenAI, Cohere, HuggingFace providers

**Audit Hook**:

- `audit.event` for `embedding.requested`
- Include: `provider`, `model`, `batch_size`

**Current State**: ✅ Fully implemented in `libs/embeddings/` with:

- **BaseEmbeddingProvider** interface for provider-agnostic design
- **OpenAI Provider**: Supports text-embedding-3-small/large and ada-002
- Automatic batch processing (configurable batch size)
- Built-in retries with exponential backoff (via OpenAI client)
- Cost tracking and estimation per request
- Comprehensive audit logging for all operations
- 19 tests passing with 88% coverage
- Complete examples including full pipeline integration
- Integrates seamlessly with extractors and chunker libraries

## 2.5 Vector Store Adapter

**Status**: ✅ Built | **Priority**: P0 (Critical)

**Responsibility**: Upsert/query/delete embeddings and metadata.

**Contract**:

- `upsert(namespace, [{id, embedding, metadata}])`
- `query(namespace, vector, top_k, filter) -> [{id, score, metadata}]`
- `delete(ids[])`
- `count(namespace)`
- `health_check()`

**Persistence Choices**:

- Allow pluggable adapters: SQLite+FAISS, Chroma, Supabase Vector, Pinecone
- Start with SQLite/FAISS for dev, Supabase/managed for prod

**Audit Hook**:

- `vectorstore.upsert` and `vectorstore.query` events
- Redact embeddings in logs; include `id`, `top_k`, `filter`, `latency`

**Current State**: ✅ Fully implemented in `libs/vectorstore/` with:

- **BaseVectorStore** interface for provider-agnostic design
- **ChromaDB Adapter**: Full CRUD operations with persistent storage
- Upsert, query, delete, count, clear operations
- Metadata filtering with ChromaDB where clauses
- Cosine, L2, and inner product distance metrics
- Similarity search with configurable top_k
- Health checks with collection stats
- Comprehensive audit logging (embeddings redacted for security)
- Auto-persistence to disk
- 32 tests passing with 80% coverage
- Complete examples including full RAG pipeline
- Ready for additional adapters (FAISS, Pinecone, Weaviate, Supabase)

## 2.6 Metadata Store / Chat Session Store

**Status**: ⏳ Not Started | **Priority**: P1 (High)

**Responsibility**: Persistent storage for chatbot sessions, conversation history, user preferences, and upload metadata.

**Contract**:

- REST or DB API
- Store session objects with indexes on: `user_id`, `session_id`, `last_activity`

**Storage**:

- SQLite for local/dev
- Postgres (or Supabase) for staging/prod

**Audit Hook**:

- `chat.session.created`
- `chat.message.sent`

**Next Steps**: Build simple SQLAlchemy models for sessions, messages, and document metadata.

## 2.7 Job Orchestrator / Worker Queue

**Status**: ⏳ Not Started | **Priority**: P1 (High)

**Responsibility**: Background job processing (extract -> chunk -> embed -> upsert) with retry, idempotency, and backpressure.

**Contract**:

- Jobs must be idempotent
- Accept `job_id` and `idempotency_key`

**Implementation Options**:

- Redis queues, RQ, Celery, or lightweight Python/Go worker
- Provide health endpoints

**Audit Hook**:

- Job lifecycle events: `job.queued`, `job.started`, `job.failed`, `job.completed`

**Next Steps**: Start with simple in-process queue for MVP, then add Redis/RQ for production.

## 2.8 Auth & RBAC

**Status**: ✅ Built | **Priority**: P1 (High)

**Responsibility**: Authenticate users and service tokens, authorize actions via RBAC policies.

**Contract**:

- Issue JWTs with scopes/roles
- Provide introspection endpoint and policy SDK

**Roles (starter)**:

- `admin`, `ingest`, `viewer`, `reader`, `service`

**Audit Hook**:

- `auth.token.issued`
- `auth.failed`
- `auth.decision` for critical operations

**Current State**: ✅ Fully implemented in `services/auth-secrets-service/` with JWT, RBAC middleware, OAuth2, and comprehensive audit logging.

## 2.9 Rate Limiter

**Status**: 🔨 Partial | **Priority**: P2 (Medium)

**Responsibility**: Limit requests per user/service (IP, user, API key), protect embedding and model usage costs.

**Contract**:

- Pluggable algorithms: token bucket and sliding window
- Expose: `check(key, cost)` and `reserve(key, cost)`

**Audit Hook**:

- `ratelimit.blocked`

**Current State**: Basic rate limiting exists in `services/auth-secrets-service/app/middleware/rate_limit.py` but needs enhancement for cost-aware limiting.

## 2.10 Audit Logging & Event Bus

**Status**: ✅ Built | **Priority**: P1 (High)

**Responsibility**: Centralize audit events, ship to pluggable backends (files, Elasticsearch, S3, SIEM).

**Contract**:

- `audit.emit(event_type, actor, context, outcome)`
- Ensure every sensitive action emits an event before/after

**Format**:

- JSON lines with: `timestamp`, `event_type`, `actor`, `resource`, `action`, `outcome`, `trace_id`

**Retention**:

- Configurable retention policy & redaction rules

**Current State**: ✅ Fully implemented in `services/auth-secrets-service/app/audit/` with pluggable storage backends and comprehensive event tracking. Also integrated in `libs/downloader/`.

## 2.11 API Gateway / API Service

**Status**: ✅ Built | **Priority**: P0 (Critical)

**Responsibility**: Public surface for ingest, chat, admin, health, metrics. Provide OpenAPI spec and run contract tests.

**Contract**:

- OpenAPI-first with strict schemas
- Each endpoint must validate input and return typed responses

**Health & Readiness**:

- `GET /health`
- `GET /ready`

**Audit Hook**:

- API-level request ID and trace injection

**Current State**: ✅ Fully implemented in `services/rag-api/` with:

- **Complete RAG Pipeline Integration**: Ties together all gundy-ai libraries
- **Document Ingestion**: `POST /documents/ingest` - Upload and process (TXT, PDF, DOCX)
- **Semantic Search**: `POST /search` - Query with similarity search and filters
- **Health Monitoring**: `GET /health` - Check all pipeline components
- **Statistics**: `GET /stats` - Pipeline metrics and info
- **FastAPI with OpenAPI**: Auto-generated docs at `/docs` and `/redoc`
- **CORS Support**: Ready for frontend integration
- **Structured Logging**: Full audit trail with structlog
- **Type-Safe**: Pydantic models for all requests/responses
- **Example Client**: Python client for easy API interaction
- **Tests**: Basic integration tests included
- Production-ready architecture with proper error handling

## 2.12 Metrics & Observability

**Status**: ⏳ Not Started | **Priority**: P2 (Medium)

**Responsibility**: Collect SLIs/metrics for latency, error rate, embedding volume, cost, job queue depth.

**Contract**:

- Expose Prometheus metrics and logs
- Dashboards for SLOs

**Next Steps**: Add Prometheus instrumentation to all services, create Grafana dashboards.

## 2.13 Secrets Manager

**Status**: ✅ Built | **Priority**: P1 (High)

**Responsibility**: Store provider keys, rotate secrets, support multiple backends (AWS KMS, Vault, ENV in dev).

**Current State**: ✅ Fully implemented in `services/auth-secrets-service/app/providers/` with support for AWS Secrets Manager, HashiCorp Vault, and environment variables.

## 2.14 CLI & SDK

**Status**: ⏳ Not Started | **Priority**: P2 (Medium)

**Responsibility**: Tooling for local dev, ingestion, health checks, quick queries.

**Contract**:

- Parity with API
- Environment-aware (dev/staging/prod)
- Include `--dry-run` and `--preview` flags

**Next Steps**: Build CLI using typer or click, SDK as thin wrapper around HTTP client.

## 2.15 CI/CD, Tests & Dependency Management

**Status**: 🔨 Partial | **Priority**: P1 (High)

**Responsibility**: Reproducible builds (lockfiles), CI gates (lint, unit, integration, contract tests), container images.

**Contract**:

- Lockfiles (poetry/pip-tools/pipenv)
- Dockerfile with pinned base images

**Current State**: Poetry configs exist, linting configured (ruff, black, prettier, eslint). Needs comprehensive test suite and CI pipeline.

## 2.16 Feature Flags & Migrations

**Status**: ⏳ Not Started | **Priority**: P3 (Low)

**Responsibility**: Gate new features, support schema migrations, and rollbacks.

**Next Steps**: Implement simple feature flag system (environment-based initially), add Alembic for DB migrations.

---

## Build Priority Summary

### P0 (Critical) - Build First for RAG MVP

1. **Extractors / Parsers** (2.2) - Core data pipeline
2. **Chunker** (2.3) - Core data pipeline
3. **Embedding Service** (2.4) - Core data pipeline
4. **Vector Store Adapter** (2.5) - Core data pipeline
5. **API Gateway** (2.11) - Complete RAG endpoints

### P1 (High) - Production Readiness

1. **Ingest Service** (2.1) - Complete with job orchestration
2. **Metadata Store** (2.6) - Session and document persistence
3. **Job Orchestrator** (2.7) - Background processing
4. **CI/CD & Tests** (2.15) - Quality gates

### P2 (Medium) - Enhancements

1. **Rate Limiter** (2.9) - Cost control
2. **Metrics & Observability** (2.12) - Production monitoring
3. **CLI & SDK** (2.14) - Developer experience

### P3 (Low) - Future

1. **Feature Flags & Migrations** (2.16) - Advanced deployment control
