# Semantic Chunking Requirements

## Overview

This document specifies requirements for implementing semantic chunking in the `gundy-ai-chunker` library. Semantic chunking splits text based on semantic similarity and meaning rather than simple token/character boundaries, creating more coherent and contextually meaningful chunks for RAG applications.

## Problem Statement

Current chunking strategies (token-aware, fixed-size) split text mechanically at token or character boundaries without considering semantic coherence. This can result in:

- **Mid-sentence splits**: Breaking semantic units
- **Context fragmentation**: Related ideas split across chunks
- **Poor retrieval quality**: Semantically incomplete chunks reduce RAG accuracy
- **Suboptimal embeddings**: Chunks lack semantic completeness

## Goals

### Business Goals
- Improve RAG retrieval accuracy by 15-20% through semantically coherent chunks
- Reduce downstream prompt engineering effort by providing better context
- Enable teams to build more intelligent document processing pipelines

### Developer Goals
- Simple API consistent with existing chunkers (`TokenAwareChunker`, `FixedSizeChunker`)
- Configurable semantic similarity thresholds
- Support for multiple embedding models (local and remote)
- Transparent performance characteristics and trade-offs
- Full audit logging and observability

### Non-Goals
- Not a document understanding or summarization system
- Not replacing token-aware chunking (semantic is complementary)
- Not providing embedding storage (only chunking logic)
- Not supporting real-time streaming (batch processing only)

## Core Capabilities

### 1. Semantic Splitting

**Requirement**: Split text into semantically coherent chunks using embedding-based similarity.

**Algorithm**:
1. Split text into candidate units (sentences or paragraphs)
2. Generate embeddings for each unit
3. Compute pairwise similarity between adjacent units
4. Merge adjacent units while similarity > threshold AND within token limits
5. Create final chunks with metadata

**Parameters**:
- `similarity_threshold` (float, 0.0-1.0): Minimum cosine similarity to merge units (default: 0.75)
- `unit_type` (str): "sentence" or "paragraph" for initial splitting (default: "sentence")
- `min_tokens` (int): Minimum chunk size in tokens (default: 100)
- `max_tokens` (int): Maximum chunk size in tokens (default: 512)
- `overlap_sentences` (int): Number of sentences to overlap between chunks (default: 1)

### 2. Embedding Model Support

**Requirement**: Support multiple embedding providers with pluggable interface.

**Local Models** (via sentence-transformers):
- `all-MiniLM-L6-v2` (default) - Fast, 384 dimensions, good quality
- `all-mpnet-base-v2` - Higher quality, 768 dimensions, slower
- `multi-qa-MiniLM-L6-cos-v1` - Optimized for Q&A retrieval
- Custom HuggingFace models by name

**Remote Providers** (via callable):
- OpenAI embeddings (text-embedding-ada-002, text-embedding-3-small/large)
- Cohere embeddings
- Custom embedding APIs via callback function

**Interface**:
```python
from typing import List, Callable

EmbeddingFunction = Callable[[List[str]], List[List[float]]]

# Local model (default)
chunker = SemanticChunker(model="all-MiniLM-L6-v2")

# Remote provider
def openai_embeddings(texts: List[str]) -> List[List[float]]:
    # Call OpenAI API
    pass

chunker = SemanticChunker(embedding_function=openai_embeddings)
```

### 3. Sentence/Paragraph Detection

**Requirement**: Intelligently split text into candidate units.

**Sentence Detection**:
- Use `nltk.sent_tokenize` or `spacy` for robust sentence boundary detection
- Handle abbreviations (Dr., Mr., etc.)
- Handle URLs and special characters
- Support multiple languages (en, es, fr, de, etc.)

**Paragraph Detection**:
- Split on double newlines (`\n\n`)
- Respect markdown/HTML structure if present
- Handle code blocks and lists

**Fallback**: If detection fails, fallback to character-based splitting with warning.

### 4. Token-Aware Sizing

**Requirement**: Respect token limits while maximizing semantic coherence.

- Use `tiktoken` for accurate token counting (same as `TokenAwareChunker`)
- Support same encodings: `cl100k_base`, `p50k_base`, `r50k_base`
- Never exceed `max_tokens` constraint
- Emit warning if chunk is below `min_tokens` (but still create it)
- Gracefully handle edge cases (very long sentences, etc.)

### 5. Metadata and Traceability

**Requirement**: Include rich metadata for debugging and analysis.

Each `TextChunk` must include:
```python
{
    "chunk_id": "doc_semantic_0001",
    "text": "...",
    "token_count": 342,
    "char_count": 1543,
    "chunk_index": 0,
    "span_start": 0,
    "span_end": 1543,
    "metadata": {
        "strategy": "semantic",
        "similarity_threshold": 0.75,
        "unit_type": "sentence",
        "sentence_count": 8,
        "avg_similarity": 0.82,  # Average similarity within chunk
        "min_similarity": 0.76,  # Minimum similarity (boundary)
        "embedding_model": "all-MiniLM-L6-v2",
        "merged_units": 8,  # Number of sentences/paragraphs merged
        "split_reason": "token_limit" | "similarity_threshold"
    }
}
```

## API Design

### SemanticChunker Class

```python
from gundy_ai.chunker import SemanticChunker, TextChunk
from typing import List, Optional, Callable

class SemanticChunker(BaseChunker):
    """Semantic chunking based on embedding similarity.
    
    Splits text into semantically coherent chunks by:
    1. Splitting into sentences or paragraphs
    2. Computing embeddings for each unit
    3. Merging adjacent units with high similarity
    4. Respecting token limits
    
    Args:
        similarity_threshold: Minimum cosine similarity to merge (0.0-1.0)
        unit_type: "sentence" or "paragraph" for initial split
        min_tokens: Minimum chunk size in tokens
        max_tokens: Maximum chunk size in tokens
        overlap_sentences: Number of sentences to overlap between chunks
        model: HuggingFace model name for local embeddings
        embedding_function: Custom embedding function for remote providers
        encoding_name: Tiktoken encoding for token counting
        batch_size: Batch size for embedding generation
    
    Example:
        >>> chunker = SemanticChunker(
        ...     similarity_threshold=0.75,
        ...     max_tokens=512
        ... )
        >>> chunks = chunker.chunk(long_text)
        >>> print(f"Created {len(chunks)} semantic chunks")
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.75,
        unit_type: str = "sentence",
        min_tokens: int = 100,
        max_tokens: int = 512,
        overlap_sentences: int = 1,
        model: Optional[str] = "all-MiniLM-L6-v2",
        embedding_function: Optional[Callable] = None,
        encoding_name: str = "cl100k_base",
        batch_size: int = 32,
    ):
        """Initialize semantic chunker."""
        pass
    
    def chunk(self, text: str, **kwargs) -> List[TextChunk]:
        """Split text into semantic chunks.
        
        Args:
            text: Text to chunk
            **kwargs: Override default parameters for this call
        
        Returns:
            List of TextChunk objects with semantic metadata
        
        Raises:
            ValueError: If text is empty or parameters invalid
            RuntimeError: If embedding model fails to load
        """
        pass
    
    def estimate_chunks(self, text: str) -> int:
        """Estimate number of chunks (conservative estimate).
        
        Note: Semantic chunking is dynamic, so this is approximate.
        Uses min_tokens to provide upper bound estimate.
        """
        pass
```

### Usage Examples

#### Basic Usage
```python
from gundy_ai.chunker import SemanticChunker

chunker = SemanticChunker()
text = "Long document text with multiple paragraphs..."
chunks = chunker.chunk(text)

for chunk in chunks:
    print(f"Chunk {chunk.chunk_index}: {chunk.token_count} tokens")
    print(f"Avg similarity: {chunk.metadata['avg_similarity']:.2f}")
```

#### Custom Similarity Threshold
```python
# Higher threshold = more coherent but smaller chunks
strict_chunker = SemanticChunker(similarity_threshold=0.85)

# Lower threshold = larger but less coherent chunks
relaxed_chunker = SemanticChunker(similarity_threshold=0.65)
```

#### Paragraph-Level Chunking
```python
# Better for documents with clear paragraph structure
chunker = SemanticChunker(
    unit_type="paragraph",
    max_tokens=1024
)
```

#### Remote Embeddings (OpenAI)
```python
from openai import OpenAI

client = OpenAI()

def openai_embed(texts: List[str]) -> List[List[float]]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]

chunker = SemanticChunker(
    embedding_function=openai_embed,
    model=None  # Disable local model
)
```

#### Integration with Extractors
```python
from gundy_ai.extractors import ParserRegistry
from gundy_ai.chunker import SemanticChunker

# Extract PDF
registry = ParserRegistry()
parser = registry.get_parser(".pdf")
pages = parser.parse("document.pdf")

# Semantic chunking
chunker = SemanticChunker(max_tokens=512)

all_chunks = []
for page in pages:
    chunks = chunker.chunk(page.text)
    all_chunks.extend(chunks)

print(f"Created {len(all_chunks)} semantic chunks from {len(pages)} pages")
```

## Architecture

### Component Structure

```
libs/chunker/src/gundy_ai/chunker/
├── __init__.py          # Export SemanticChunker
├── base.py              # BaseChunker interface (no changes)
├── models.py            # TextChunk, ChunkerConfig (no changes)
├── semantic.py          # NEW: SemanticChunker implementation
├── semantic_utils.py    # NEW: Sentence splitting, similarity computation
├── embeddings.py        # NEW: Embedding provider interfaces
├── token_aware.py       # Existing
├── fixed_size.py        # Existing
└── audit.py             # Update with semantic events
```

### Dependencies

Add to `pyproject.toml`:
```toml
[tool.poetry.dependencies]
sentence-transformers = ">=2.2,<3.0"  # Local embeddings
nltk = ">=3.8,<4.0"                   # Sentence tokenization
numpy = ">=1.24,<2.0"                 # Array operations
scikit-learn = ">=1.3,<2.0"           # Cosine similarity

[tool.poetry.group.dev.dependencies]
spacy = {version = ">=3.7,<4.0", optional = true}  # Optional: better sentence detection
```

### Key Algorithms

#### 1. Semantic Merging Algorithm
```
Input: list of candidate units (sentences/paragraphs)
Output: list of semantic chunks

1. Initialize empty chunks list
2. Initialize current_chunk = [first unit]
3. For each subsequent unit:
   a. Compute embedding for current_chunk and next unit
   b. Calculate cosine similarity
   c. Estimate tokens if merged
   d. If similarity > threshold AND tokens < max_tokens:
      - Merge unit into current_chunk
   e. Else:
      - Finalize current_chunk as a chunk
      - Start new current_chunk with overlap
4. Finalize remaining current_chunk
5. Return chunks
```

#### 2. Cosine Similarity Computation
```python
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """Compute cosine similarity between two embeddings."""
    vec1 = np.array(embedding1).reshape(1, -1)
    vec2 = np.array(embedding2).reshape(1, -1)
    return float(cosine_similarity(vec1, vec2)[0][0])
```

#### 3. Chunk Overlap Strategy
```
Overlap Strategy:
- After creating a chunk, take the last N sentences
- Use them as the start of the next chunk
- Preserves context across chunk boundaries
- N configurable via overlap_sentences parameter
```

## Performance Requirements

### Latency Targets
- **Small texts** (<5K chars): <500ms including embedding generation
- **Medium texts** (50K chars): <3 seconds
- **Large texts** (500K chars): <30 seconds

### Memory Constraints
- Maximum memory usage: 2GB for 1MB input text
- Batch embedding generation to avoid OOM
- Stream-process very large documents if possible

### Embedding Performance
- **Local models**: ~100-500 sentences/second on CPU
- **Remote APIs**: Limited by API rate limits (track quota)
- **Batch optimization**: Embed multiple units in single call

### Scalability
- Support documents up to 10MB (plain text)
- Gracefully degrade for very large documents (warning + chunking)
- Provide progress callbacks for long operations

## Testing Requirements

### Unit Tests

1. **Sentence/Paragraph Splitting**
   - Test various punctuation marks
   - Test abbreviations (Dr., Mr., etc.)
   - Test URLs and special characters
   - Test edge cases (empty text, single sentence)

2. **Semantic Merging**
   - Test similarity threshold enforcement
   - Test token limit respect
   - Test overlap generation
   - Test metadata population

3. **Embedding Integration**
   - Mock local model loading
   - Mock remote API calls
   - Test error handling (model load failure, API errors)
   - Test different embedding dimensions

4. **Token Counting**
   - Test different encodings
   - Test max_tokens enforcement
   - Test min_tokens warnings

### Integration Tests

1. **End-to-End Chunking**
   - Process sample documents (1KB, 10KB, 100KB)
   - Verify all chunks within token limits
   - Verify semantic coherence (manual review)
   - Compare with token-aware chunking

2. **Model Compatibility**
   - Test with multiple local models
   - Test with mock remote providers
   - Test model switching

3. **Error Recovery**
   - Test with malformed text
   - Test with unsupported languages
   - Test with embedding API failures

### Performance Tests

1. **Latency Benchmarks**
   - Measure chunking time vs text size
   - Compare local vs remote embedding latency
   - Profile bottlenecks

2. **Memory Usage**
   - Monitor memory during large document processing
   - Test with concurrent chunking operations

### Golden File Tests

Create reference corpus:
- `tests/data/semantic/sample1.txt` - Technical document
- `tests/data/semantic/sample2.txt` - Narrative text
- `tests/data/semantic/sample3.txt` - Mixed content
- `tests/data/semantic/expected_chunks_*.json` - Expected outputs

## Security & Privacy

### Data Handling
- **No persistent storage**: Embeddings computed on-demand, not cached by default
- **Local-first default**: Use local models by default to avoid data leakage
- **Remote provider warnings**: Emit audit event when using remote embeddings
- **PII awareness**: Document that semantic chunking may group sensitive data

### Model Security
- **Verify model checksums**: Validate sentence-transformers models on download
- **Sandboxed execution**: Models run in same process (no additional isolation)
- **Dependency scanning**: Regular CVE checks on ML dependencies

### Rate Limiting
- **Remote API respect**: Honor rate limits for remote embedding providers
- **Configurable timeouts**: Allow setting max wait time for embeddings
- **Quota tracking**: Emit metrics for embedding API usage

## Audit & Observability

### Audit Events

Add to `audit.py`:
```python
class ChunkingEventType(str, Enum):
    SEMANTIC_CHUNKING_STARTED = "chunking.semantic.started"
    SEMANTIC_CHUNKING_COMPLETED = "chunking.semantic.completed"
    SEMANTIC_CHUNKING_FAILED = "chunking.semantic.failed"
    EMBEDDING_GENERATED = "chunking.semantic.embedding_generated"
    SIMILARITY_COMPUTED = "chunking.semantic.similarity_computed"
```

### Event Payload
```python
{
    "event_type": "chunking.semantic.completed",
    "timestamp": "2025-10-23T12:34:56Z",
    "trace_id": "abc-123",
    "input_length_chars": 50000,
    "input_length_tokens": 12500,
    "chunks_created": 25,
    "avg_chunk_tokens": 500,
    "avg_similarity": 0.78,
    "min_similarity": 0.75,
    "max_similarity": 0.95,
    "embedding_model": "all-MiniLM-L6-v2",
    "embedding_provider": "local",
    "units_processed": 200,
    "units_merged": 175,
    "processing_time_ms": 2341,
    "embedding_time_ms": 1876,
    "similarity_time_ms": 234,
    "outcome": "success"
}
```

### Logging
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "semantic_chunking_started",
    text_length=len(text),
    similarity_threshold=self.similarity_threshold,
    unit_type=self.unit_type,
    model=self.model
)

logger.info(
    "semantic_chunking_completed",
    chunks_created=len(chunks),
    avg_tokens=avg_tokens,
    processing_time=elapsed
)
```

## Cost Considerations

### Local Models (Recommended)
- **Infrastructure**: CPU/GPU on application server
- **Cost**: Zero per-request (one-time model download)
- **Latency**: 100-500ms for typical document
- **Trade-off**: Slightly lower quality than large remote models

### Remote Models (OpenAI, Cohere)
- **Infrastructure**: API calls to external service
- **Cost**: ~$0.0001 per 1K tokens (OpenAI text-embedding-3-small)
- **Latency**: 200-500ms per API call + network
- **Trade-off**: Higher quality, but cost scales with usage

### Recommendations
1. **Default to local**: Use `all-MiniLM-L6-v2` for most use cases
2. **Remote for quality**: Use OpenAI embeddings for high-stakes RAG
3. **Hybrid approach**: Use local for chunking, remote for final embeddings

## Migration & Compatibility

### Backward Compatibility
- Existing chunkers (`TokenAwareChunker`, `FixedSizeChunker`) unchanged
- Same `BaseChunker` interface, same `TextChunk` model
- No breaking changes to public API

### Migration Path
```python
# Old approach
from gundy_ai.chunker import TokenAwareChunker
chunker = TokenAwareChunker(max_tokens=512)

# New approach (drop-in replacement with better quality)
from gundy_ai.chunker import SemanticChunker
chunker = SemanticChunker(max_tokens=512)

# Same interface
chunks = chunker.chunk(text)
```

### Version Constraints
- Minimum version: `gundy-ai-chunker>=0.2.0`
- Semantic versioning: MINOR bump (new feature, no breaking changes)
- Deprecation: None (additive change)

## Documentation Requirements

### README Updates
- Add semantic chunking to feature list
- Update quick start with semantic example
- Add comparison table (semantic vs token-aware vs fixed-size)
- Update API reference

### New Documentation
- `docs/semantic-chunking-guide.md` - Comprehensive guide
  - When to use semantic chunking
  - Configuring similarity thresholds
  - Choosing embedding models
  - Performance tuning
  - Troubleshooting

### Examples
- `examples/semantic_basic.py` - Basic usage
- `examples/semantic_advanced.py` - Custom embeddings, tuning
- `examples/semantic_comparison.py` - Compare with other strategies
- `examples/semantic_rag_pipeline.py` - Full RAG integration

## Success Metrics

### Functional Metrics
- ✅ All chunks respect max_tokens constraint (100% compliance)
- ✅ Average chunk coherence score > 0.75 (manual evaluation)
- ✅ No crashes on corpus of 1000+ diverse documents (100% reliability)

### Quality Metrics
- 📊 RAG retrieval accuracy improvement: target 15-20% vs token-aware
- 📊 Chunk boundary quality: >90% of splits at natural semantic boundaries
- 📊 Developer satisfaction: survey feedback from 3+ adopting teams

### Performance Metrics
- ⚡ Latency: <3s for 50K char document (local model)
- ⚡ Memory: <2GB for 1MB document
- ⚡ Throughput: >10 documents/minute on standard hardware

### Adoption Metrics
- 🎯 Used by 3+ teams within 3 months of release
- 🎯 50%+ of new RAG pipelines use semantic chunking
- 🎯 Zero critical bugs reported in first 2 months

## Implementation Phases

### Phase 1: Core Implementation (Weeks 1-2)
- [ ] Implement `SemanticChunker` class skeleton
- [ ] Add sentence/paragraph splitting logic
- [ ] Integrate sentence-transformers for local embeddings
- [ ] Implement similarity-based merging algorithm
- [ ] Add token counting and limit enforcement
- [ ] Unit tests for core logic

### Phase 2: Embedding Providers (Week 3)
- [ ] Define `EmbeddingFunction` interface
- [ ] Implement local model loader with caching
- [ ] Support custom embedding functions
- [ ] Add batch processing for embeddings
- [ ] Error handling and retries
- [ ] Unit tests for embedding integration

### Phase 3: Metadata & Observability (Week 4)
- [ ] Populate comprehensive chunk metadata
- [ ] Add audit event emissions
- [ ] Implement structured logging
- [ ] Add performance metrics collection
- [ ] Integration tests for observability

### Phase 4: Testing & Validation (Week 5)
- [ ] Golden file tests with reference corpus
- [ ] Performance benchmarks
- [ ] Memory profiling
- [ ] End-to-end integration tests
- [ ] Manual quality review of sample chunks

### Phase 5: Documentation & Examples (Week 6)
- [ ] Update README with semantic chunking
- [ ] Create semantic chunking guide
- [ ] Write example scripts
- [ ] Add API documentation
- [ ] Create migration guide

### Phase 6: Polish & Release (Week 7)
- [ ] Address feedback from internal testing
- [ ] Optimize performance bottlenecks
- [ ] Final security review
- [ ] Version bump and release notes
- [ ] Announce to internal teams

## Open Questions & Design Decisions

### 1. Default Similarity Threshold
**Question**: What should the default threshold be?

**Options**:
- 0.70 - More aggressive merging, larger chunks
- 0.75 - Balanced (recommended)
- 0.80 - Conservative, smaller chunks

**Recommendation**: 0.75 based on preliminary testing

### 2. Embedding Model Size
**Question**: Which default model balances quality and performance?

**Options**:
- `all-MiniLM-L6-v2` - 384 dim, fast, good quality (recommended)
- `all-mpnet-base-v2` - 768 dim, slower, better quality
- `multi-qa-MiniLM-L6-cos-v1` - 384 dim, optimized for Q&A

**Recommendation**: `all-MiniLM-L6-v2` as default, allow override

### 3. Sentence vs Paragraph Default
**Question**: Should default unit be sentence or paragraph?

**Analysis**:
- Sentences: More granular control, better merging
- Paragraphs: Faster, fewer embeddings needed

**Recommendation**: Sentence (more flexible, better quality)

### 4. Overlap Strategy
**Question**: How should overlaps be handled?

**Options**:
- No overlap (faster, no redundancy)
- Sentence-based overlap (recommended)
- Token-based overlap (like TokenAwareChunker)

**Recommendation**: Sentence-based (1 sentence default)

### 5. Embedding Caching
**Question**: Should we cache embeddings between runs?

**Considerations**:
- Pro: Faster re-chunking of same document
- Con: Memory/storage overhead, cache invalidation complexity
- Con: Privacy concerns (persistent embeddings)

**Recommendation**: No caching by default, allow opt-in later

## Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Slow embedding generation | High | Medium | Use local models, batch processing, progress callbacks |
| Poor chunk quality | High | Low | Extensive testing, tunable thresholds, fallback to token-aware |
| Model download failures | Medium | Low | Bundle model with package, retry logic, clear error messages |
| Memory exhaustion | High | Low | Batch processing, memory limits, document size warnings |
| Breaking API changes | High | Very Low | Extend BaseChunker, no changes to existing chunkers |
| Remote API rate limits | Medium | Medium | Local models default, rate limit handling, exponential backoff |

## References

### Academic Papers
- [Semantic Text Segmentation (Hearst, 1997)](https://www.aclweb.org/anthology/J97-1003/)
- [TextTiling: Segmenting Text into Multi-paragraph Subtopic Passages](https://www.cs.cmu.edu/~./sofus/semantic_text_segmentation.html)

### Industry Best Practices
- [LangChain Semantic Chunking](https://python.langchain.com/docs/modules/data_connection/document_transformers/semantic-chunker)
- [LlamaIndex Semantic Splitter](https://docs.llamaindex.ai/en/stable/examples/node_parsers/semantic_splitter/)

### Internal Documentation
- `docs/chunk-splitting-guide.md` - Token limit handling
- `docs/text-extract-chunk.md` - Original PRD with semantic chunking vision
- `libs/chunker/README.md` - Existing chunker library documentation

## Appendix: Configuration Examples

### Conservative (High Quality, Small Chunks)
```python
chunker = SemanticChunker(
    similarity_threshold=0.85,  # Strict coherence
    max_tokens=256,             # Smaller chunks
    min_tokens=100,
    overlap_sentences=2         # More context preservation
)
```

### Balanced (Recommended)
```python
chunker = SemanticChunker(
    similarity_threshold=0.75,  # Balanced
    max_tokens=512,             # Standard size
    min_tokens=100,
    overlap_sentences=1
)
```

### Aggressive (Large Chunks, Fast)
```python
chunker = SemanticChunker(
    similarity_threshold=0.65,  # Relaxed merging
    max_tokens=1024,            # Larger chunks
    min_tokens=200,
    unit_type="paragraph",      # Faster splitting
    overlap_sentences=0         # No overlap
)
```

### High-Quality RAG
```python
from openai import OpenAI

client = OpenAI()

def openai_embed(texts: List[str]) -> List[List[float]]:
    response = client.embeddings.create(
        model="text-embedding-3-large",
        input=texts
    )
    return [item.embedding for item in response.data]

chunker = SemanticChunker(
    similarity_threshold=0.80,
    max_tokens=512,
    embedding_function=openai_embed,
    model=None
)
```

---

## Approval & Sign-off

**Document Version**: 1.0  
**Created**: 2025-10-23  
**Status**: Draft - Ready for Review

**Reviewers**:
- [ ] Engineering Lead - Architecture approval
- [ ] ML Engineer - Embedding strategy review
- [ ] Product - Requirements validation
- [ ] Security - Privacy and data handling review

**Next Steps**:
1. Review and approval from stakeholders
2. Update project roadmap with implementation phases
3. Create implementation tickets
4. Begin Phase 1 development
