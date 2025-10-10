# Gundy AI Chunker

Token-aware text chunking for AI applications with support for multiple strategies.

## Features

- **Token-Aware Chunking**: Respects LLM token limits using tiktoken
- **Fixed-Size Chunking**: Character-based chunking for simple use cases
- **Configurable Overlap**: Maintain context between chunks
- **Multiple Strategies**: Choose the right approach for your use case
- **Audit Logging**: Track all chunking operations
- **Type Safety**: Full Pydantic models with validation
- **High Performance**: Optimized for large documents

## Installation

```bash
poetry add gundy-ai-chunker
```

## Quick Start

```python
from gundy_ai.chunker import TokenAwareChunker

# Create chunker
chunker = TokenAwareChunker(
    max_tokens=512,
    overlap_tokens=50
)

# Chunk text
text = "Your long document text here..."
chunks = chunker.chunk(text)

# Access chunks
for chunk in chunks:
    print(f"Tokens: {chunk.token_count}")
    print(f"Text: {chunk.text[:100]}")
```

## Chunking Strategies

### Token-Aware (Recommended for LLMs)

Uses tiktoken for accurate token counting. Ensures chunks never exceed LLM token limits.
Perfect for preparing text for OpenAI, Anthropic, or other LLM APIs.

```python
from gundy_ai.chunker import TokenAwareChunker

chunker = TokenAwareChunker(
    max_tokens=512,
    overlap_tokens=50,
    encoding_name="cl100k_base"  # GPT-4/GPT-3.5
)

chunks = chunker.chunk(text)

# Each chunk respects token limits
for chunk in chunks:
    assert chunk.token_count <= 512
```

**Supported Encodings**:

- `cl100k_base` - GPT-4, GPT-3.5-turbo, text-embedding-ada-002
- `p50k_base` - Codex models
- `r50k_base` - GPT-3 models (davinci, curie, etc.)

### Fixed-Size (Simpler Alternative)

Character-based chunking for simpler use cases where token limits aren't critical.

```python
from gundy_ai.chunker import FixedSizeChunker

chunker = FixedSizeChunker(
    chunk_size=1000,
    overlap_size=100
)

chunks = chunker.chunk(text)
```

## Integration with Extractors

Works seamlessly with `gundy-ai-extractors`:

```python
from gundy_ai.extractors import ParserRegistry, PDFParser
from gundy_ai.chunker import TokenAwareChunker

# Extract text from PDF
registry = ParserRegistry()
registry.register(PDFParser())
parser = registry.get_parser(".pdf")
extracted = parser.parse("document.pdf")

# Chunk the extracted text
chunker = TokenAwareChunker(max_tokens=512, overlap_tokens=50)

all_chunks = []
for page in extracted:
    page_chunks = chunker.chunk(page.text)
    all_chunks.extend(page_chunks)

print(f"Total chunks: {len(all_chunks)}")
```

## API Reference

### TextChunk

Result object from chunking operations.

**Fields**:

- `chunk_id`: Unique identifier
- `text`: Chunk content
- `token_count`: Number of tokens (0 for fixed-size)
- `char_count`: Number of characters
- `chunk_index`: Position in sequence (0-based)
- `span_start`: Character offset start in original text
- `span_end`: Character offset end in original text
- `metadata`: Strategy-specific metadata

### TokenAwareChunker

**Methods**:

- `chunk(text: str) -> List[TextChunk]`: Chunk text with token limits
- `estimate_chunks(text: str) -> int`: Estimate number of chunks

**Parameters**:

- `max_tokens` (int): Maximum tokens per chunk (default: 512)
- `overlap_tokens` (int): Overlap between chunks (default: 50)
- `encoding_name` (str): Tiktoken encoding (default: "cl100k_base")

### FixedSizeChunker

**Methods**:

- `chunk(text: str) -> List[TextChunk]`: Chunk text by character count
- `estimate_chunks(text: str) -> int`: Estimate number of chunks

**Parameters**:

- `chunk_size` (int): Maximum characters per chunk (default: 1000)
- `overlap_size` (int): Overlap in characters (default: 100)

## Audit Logging

All chunking operations emit structured audit events:

- `chunking.started` - Chunking begins
- `chunking.completed` - Chunking successful
- `chunking.failed` - Chunking failed

Events include:

- Strategy used
- Input length and token count
- Chunks created
- Processing time
- Outcome and errors

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_token_aware.py -v
```

**Test Coverage**: 38 tests, 93% coverage

## Examples

See `examples/` directory:

- `basic_usage.py`: Simple chunking example
- `compare_strategies.py`: Compare token-aware vs fixed-size
- `integration_with_extractors.py`: Full extraction + chunking pipeline

## Performance

**Token-Aware Chunking**:

- Small texts (<1K chars): <1ms
- Medium texts (10K chars): ~5ms
- Large texts (100K chars): ~50ms

**Fixed-Size Chunking**:

- Faster than token-aware (no tokenization overhead)
- Linear time complexity O(n)

## Best Practices

1. **Use Token-Aware for LLMs**: When sending text to OpenAI, Anthropic, etc.
2. **Use Fixed-Size for Speed**: When token limits don't matter
3. **Set Appropriate Overlap**: 10-20% of chunk size maintains good context
4. **Estimate First**: Use `estimate_chunks()` for progress tracking
5. **Match Encoding**: Use same encoding as your target LLM

## Requirements

- Python >=3.11,<3.13
- pydantic >=2.5,<3.0
- structlog >=23.2,<25.0
- tiktoken >=0.5,<1.0

## License

See main ai-utils repository.

## Contributing

Follow the project guidelines in `.cursorrules` at repository root.
