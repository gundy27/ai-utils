# Architecture Philosophy

## Overview

ai-utils is designed as a **library ecosystem** for building AI applications, not as a monolithic application platform. This document explains the architectural decisions, patterns, and guidelines for working with and extending the ai-utils ecosystem.

## Core Principles

### 1. Libraries Over Applications

ai-utils provides **building blocks**, not complete solutions.

**What we build:**

- Generic, reusable libraries
- Well-defined interfaces and protocols
- Extensible plugin systems
- Foundational infrastructure services

**What we don't build:**

- Complete end-user applications
- Use-case specific business logic
- Opinionated product features
- Industry-specific workflows

### 2. Separation of Concerns

Libraries should have clear boundaries and responsibilities:

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│   (portfolio-chatbot, sales-assistant, etc.)            │
│   - Use-case specific logic                             │
│   - Business workflows                                   │
│   - Custom tools and integrations                        │
└────────────────────┬────────────────────────────────────┘
                     │ imports
┌────────────────────▼────────────────────────────────────┐
│                  ai-utils Libraries                      │
│   (gundy-ai-extractors, gundy-ai-chunker, etc.)        │
│   - Core functionality                                   │
│   - Generic interfaces                                   │
│   - Extensible base classes                              │
└──────────────────────────────────────────────────────────┘
```

### 3. Plugin Architecture

All components use plugin-based designs for extensibility:

```python
# Base interface
class BaseParser(ABC):
    @abstractmethod
    def parse(self, file_path: str) -> str:
        pass

# Plugin implementation
class PDFParser(BaseParser):
    def parse(self, file_path: str) -> str:
        # PDF-specific logic
        pass

# Registry for discovery
registry = ParserRegistry()
registry.register(PDFParser())
```

This allows:

- Adding new parsers without modifying core code
- Third-party extensions
- Clean testing boundaries
- Easy feature flagging

### 4. Dependency Management

Libraries should have:

- **Minimal dependencies** - Only what's absolutely necessary
- **Optional extras** - Feature-specific deps as extras (e.g., `[openai]`, `[chromadb]`)
- **Relaxed version constraints** - `>=X.Y,<Z.0` to avoid conflicts
- **No circular dependencies** - Libraries never depend on applications

Example:

```toml
[tool.poetry.dependencies]
python = ">=3.11,<3.13"
pydantic = ">=2.5,<3.0"  # Core dependency

[tool.poetry.extras]
openai = ["openai>=1.0,<2.0"]  # Optional
chromadb = ["chromadb>=0.4,<1.0"]
```

## Repository Structure

### libs/

Core reusable libraries. Each library:

- Has its own `pyproject.toml` and `README.md`
- Can be installed independently
- Includes tests and examples
- Follows semantic versioning
- Publishes to PyPI independently (future)

**Example libraries:**

- `libs/extractors` - Document parsing
- `libs/chunker` - Text chunking
- `libs/embeddings` - Embedding generation
- `libs/vectorstore` - Vector database adapters
- `libs/metadata-store` - Metadata management
- `libs/job-queue` - Background job processing

### services/

Generic infrastructure services that integrate multiple libraries:

- **rag-api**: Basic RAG API service
  - Integrates all core libraries
  - Provides generic endpoints
  - No use-case specific logic
  - Extensible via configuration

- **auth-secrets-service**: Authentication and secrets
  - OAuth2, RBAC, token management
  - Secrets storage and retrieval
  - Audit logging

### templates/

Starting points for common patterns:

- **rag-starter**: RAG chatbot template
  - Frontend + Backend boilerplate
  - Clean, minimal implementation
  - Well-documented customization points
  - No opinionated features

- **api-service-starter**: FastAPI service template
- **webapp-starter**: Next.js webapp template

Templates are **not** meant to be used directly in production. They're:

- Copied and customized
- Learning resources
- Reference implementations

## Using ai-utils Libraries

### Local Development

For local development, reference libraries by path:

```toml
[tool.poetry.dependencies]
gundy-ai-extractors = {path = "../ai-utils/libs/extractors", develop = true}
gundy-ai-chunker = {path = "../ai-utils/libs/chunker", develop = true}
```

This allows:

- Live reload during development
- Testing changes across repos
- Easier debugging

### Production Use (Future)

When libraries are published to PyPI:

```toml
[tool.poetry.dependencies]
gundy-ai-extractors = ">=0.1,<1.0"
gundy-ai-chunker = ">=0.1,<1.0"
gundy-ai-embeddings = {version = ">=0.1,<1.0", extras = ["openai"]}
```

## Creating New Applications

### When to Create a Separate Repository

Create a new application repository when you need:

1. **Use-case specific features**
   - Lead detection for portfolio chatbots
   - Industry-specific document processing
   - Custom tool integrations (Calendly, CRM, etc.)

2. **Business logic**
   - Pricing calculations
   - Workflow orchestration
   - Domain-specific validations

3. **Opinionated UI/UX**
   - Branded components
   - Specific user flows
   - Custom analytics

4. **Independent versioning**
   - Deploy without updating core libs
   - Experiment without affecting others

### Application Repository Structure

Example: `portfolio-chatbot/`

```
portfolio-chatbot/
├── pyproject.toml           # Imports gundy-ai-* libs
├── backend/
│   ├── app/
│   │   ├── main.py          # Application-specific API
│   │   ├── tools/           # Custom tools (Calendly, etc.)
│   │   ├── lead_detection.py  # Business logic
│   │   └── routers/         # Application routes
│   └── tests/
├── frontend/                # Application UI
└── docs/
```

Key points:

- **Imports** from ai-utils, doesn't modify it
- **Extends** base classes for custom behavior
- **Composes** libraries for specific workflows
- **Versions** independently

### Example: Lead Detection

**Bad** - In ai-utils:

```python
# libs/rag/lead_detection.py
def detect_lead(conversation):
    # Opinionated lead scoring logic
    if "pricing" in conversation:
        return "high_interest"
```

**Good** - In application repo:

```python
# portfolio-chatbot/backend/app/lead_detection.py
from gundy_ai.metadata_store import MetadataStore

def detect_interest_signal(conversation_history):
    # Application-specific logic
    # Uses metadata_store, but adds custom scoring
```

## Testing Strategy

### Library Tests

Each library includes:

- **Unit tests**: Test individual functions
- **Integration tests**: Test with real backends (ChromaDB, OpenAI)
- **Contract tests**: Verify interface stability

Run library tests:

```bash
cd libs/extractors
poetry run pytest
```

### Application Tests

Applications test:

- End-to-end workflows
- Business logic
- Custom integrations

```bash
cd portfolio-chatbot/backend
poetry run pytest
```

## Versioning Strategy

See [`versioning.md`](./versioning.md) for comprehensive details.

**Key principles:**

- Semantic versioning (`vMAJOR.MINOR.PATCH`)
- Libraries version independently
- Applications pin library versions
- Breaking changes require MAJOR bump

## Publishing (Future)

When ready, libraries will be published to PyPI:

```bash
cd libs/extractors
poetry build
poetry publish
```

Users can then:

```bash
pip install gundy-ai-extractors
```

## Migration Path

For moving code from ai-utils to an application:

1. **Identify**: Is this core or application-specific?
2. **Extract**: Copy files to new repository
3. **Refactor**: Update imports to use gundy-ai libraries
4. **Test**: Ensure all tests pass
5. **Document**: Update READMEs
6. **Deploy**: Application and libraries deploy independently

## Best Practices

### DO:

- ✅ Keep libraries focused and single-purpose
- ✅ Use abstract base classes for extensibility
- ✅ Provide comprehensive examples
- ✅ Maintain detailed READMEs
- ✅ Write tests for all public APIs
- ✅ Use dependency injection for testability
- ✅ Log audit events for critical operations

### DON'T:

- ❌ Add use-case specific logic to libraries
- ❌ Create tight coupling between libraries
- ❌ Include complete applications in ai-utils
- ❌ Hard-code business rules in generic code
- ❌ Make breaking changes without MAJOR version bump
- ❌ Skip documentation or tests

## Examples

### Good: Generic Chunker

```python
# libs/chunker/src/gundy_ai/chunker/token_aware.py
class TokenAwareChunker:
    def __init__(self, max_tokens: int, overlap_tokens: int):
        # Generic, configurable
        pass

    def chunk(self, text: str) -> List[str]:
        # Works for any text
        pass
```

### Good: Application-Specific Tool

```python
# portfolio-chatbot/backend/app/tools/calendly.py
class CalendlyTool(BaseTool):
    def execute(self, **kwargs):
        # Specific to this application
        return {"calendly_link": "https://..."}
```

### Bad: Opinionated Logic in Library

```python
# DON'T DO THIS in ai-utils
def chunk_medical_records(text: str):
    # Too specific for a generic library
    pass
```

## Conclusion

ai-utils is designed to be:

- **Reusable**: Libraries work in any application
- **Extensible**: Plugin systems for customization
- **Maintainable**: Clear boundaries and responsibilities
- **Testable**: Isolated components with well-defined interfaces

By keeping libraries generic and moving application-specific code to separate repositories, we maintain a clean, scalable ecosystem that benefits all users.

## Questions?

See individual library READMEs or open an issue in the ai-utils repository.
