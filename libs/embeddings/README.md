# Gundy AI Embeddings

Provider-agnostic embedding generation for AI applications with support for multiple providers.

## Features

- **Provider-Agnostic**: Unified interface for all embedding providers
- **OpenAI Integration**: Built-in support for OpenAI embeddings
- **Batch Processing**: Efficient batch embedding with automatic batching
- **Retry Logic**: Automatic retries with exponential backoff
- **Cost Tracking**: Monitor embedding costs and usage
- **Audit Logging**: Track all embedding operations
- **Type Safety**: Full Pydantic models with validation
- **Health Checks**: Verify provider connectivity and configuration

## Installation

```bash
# With OpenAI support
poetry add gundy-ai-embeddings[openai]

# Or base installation (no providers)
poetry add gundy-ai-embeddings
```

## Quick Start

```python
from gundy_ai.embeddings import OpenAIEmbeddingProvider

# Create provider
provider = OpenAIEmbeddingProvider(
    api_key="your-api-key",
    model="text-embedding-3-small"
)

# Generate embeddings
texts = ["Hello world", "AI is amazing"]
result = provider.embed(texts)

# Access embeddings
print(f"Embeddings: {len(result.embeddings)}")
print(f"Dimensions: {result.dimensions}")
print(f"Cost: ${result.estimated_cost_usd:.6f}")
```

## Supported Providers

### OpenAI

**Models**:

- `text-embedding-3-small` - 1536 dims, $0.02/1M tokens (recommended)
- `text-embedding-3-large` - 3072 dims, $0.13/1M tokens (higher quality)
- `text-embedding-ada-002` - 1536 dims, $0.10/1M tokens (legacy)

**Features**:

- Automatic batching (default: 100 texts/batch)
- Built-in retries with exponential backoff
- Cost estimation
- Health checks

```python
from gundy_ai.embeddings import OpenAIEmbeddingProvider

provider = OpenAIEmbeddingProvider(
    model="text-embedding-3-small",
    max_batch_size=100,
    timeout_seconds=60,
    max_retries=3
)
```

## Integration with Other Libraries

Works seamlessly with other gundy-ai libraries:

```python
from gundy_ai.extractors import ParserRegistry, PDFParser
from gundy_ai.chunker import TokenAwareChunker
from gundy_ai.embeddings import OpenAIEmbeddingProvider

# Extract text from PDF
registry = ParserRegistry()
registry.register(PDFParser())
extracted = registry.get_parser(".pdf").parse("doc.pdf")

# Chunk the text
chunker = TokenAwareChunker(max_tokens=512, overlap_tokens=50)
all_chunks = []
for page in extracted:
    chunks = chunker.chunk(page.text)
    all_chunks.extend(chunks)

# Generate embeddings
provider = OpenAIEmbeddingProvider()
chunk_texts = [chunk.text for chunk in all_chunks]
result = provider.embed(chunk_texts)

print(f"Embedded {len(result.embeddings)} chunks")
print(f"Total cost: ${result.estimated_cost_usd:.4f}")
```

## API Reference

### EmbeddingResult

Result object from embedding operations.

**Fields**:

- `embeddings`: List[List[float]] - Embedding vectors
- `model`: str - Model used
- `dimensions`: int - Embedding dimensionality
- `total_tokens`: int - Tokens processed
- `texts_count`: int - Number of texts
- `latency_ms`: float - Processing time
- `estimated_cost_usd`: float - Estimated cost
- `provider`: str - Provider name
- `metadata`: Dict - Provider-specific data

### OpenAIEmbeddingProvider

**Methods**:

- `embed(texts: List[str]) -> EmbeddingResult`: Generate embeddings
- `health_check() -> Dict`: Check provider health

**Properties**:

- `provider_name`: "openai"
- `model_name`: Model being used
- `dimensions`: Embedding dimensions

**Parameters**:

- `api_key`: OpenAI API key (or OPENAI_API_KEY env var)
- `model`: Model name (default: "text-embedding-3-small")
- `max_batch_size`: Batch size (default: 100)
- `timeout_seconds`: Timeout (default: 60)
- `max_retries`: Retry attempts (default: 3)

## Audit Logging

All embedding operations emit audit events:

- `embedding.requested` - Embedding generation started
- `embedding.completed` - Embeddings generated successfully
- `embedding.failed` - Embedding generation failed
- `provider.health_check` - Health check performed

Events include:

- Provider and model
- Text count and tokens
- Latency and cost
- Outcome and errors

## Testing

```bash
# Run all tests (requires OPENAI_API_KEY)
export OPENAI_API_KEY='your-key'
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run without API tests
poetry run pytest -m "not requires_api"
```

**Test Coverage**: 19 tests, 88% coverage

## Performance

- Single text: ~150ms
- Batch (100 texts): ~500ms
- Automatic batching for 1000+ texts
- Concurrent batching support (coming soon)

## Cost Estimation

Costs are automatically calculated based on token usage:

| Model                  | Dimensions | Cost (per 1M tokens) |
| ---------------------- | ---------- | -------------------- |
| text-embedding-3-small | 1536       | $0.02                |
| text-embedding-3-large | 3072       | $0.13                |
| text-embedding-ada-002 | 1536       | $0.10                |

## Examples

See `examples/` directory:

- `basic_usage.py`: Simple embedding example
- `full_pipeline.py`: Complete extraction → chunking → embedding flow

## Requirements

- Python >=3.11,<3.13
- pydantic >=2.5,<3.0
- structlog >=23.2,<25.0
- httpx >=0.25,<1.0
- openai >=1.0,<2.0 (for OpenAI provider)

## License

See main ai-utils repository.

## Contributing

Follow the project guidelines in `.cursorrules` at repository root.
