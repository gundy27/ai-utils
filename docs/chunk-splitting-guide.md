# Chunk Splitting Guide

This guide shows you how to handle documents that create chunks exceeding LLM token limits using the enhanced `data_pipelines` library.

## 🎯 Problem

When processing large documents, chunking strategies may create chunks that exceed LLM token limits:

- **OpenAI GPT-4/GPT-3.5**: 8,192 tokens
- **Claude**: 100,000+ tokens
- **Other models**: Various limits

Oversized chunks cause API errors and prevent successful processing.

## ✅ Solution

The `data_pipelines` library provides two approaches to handle this:

1. **ChunkSplittingFilter** - Split existing oversized chunks
2. **TokenAwareChunker** - Create token-aware chunks from the start

## 🚀 Quick Start

### Option 1: Chunk Splitting Filter

Use this to fix existing documents with oversized chunks:

```python
from gundy_ai.data_pipelines import ChunkSplittingFilter

# Create filter with OpenAI limits
filter = ChunkSplittingFilter(
    max_tokens=8192,      # Hard limit (OpenAI)
    target_tokens=4000,   # Target size for split chunks
    overlap_tokens=200    # Overlap between chunks
)

# Apply to document with oversized chunks
filtered_doc = await filter.filter_document(document)

print(f"Original chunks: {len(document.chunks)}")
print(f"After splitting: {len(filtered_doc.chunks)}")
```

### Option 2: Token-Aware Chunking

Use this for new documents to prevent oversized chunks:

```python
from gundy_ai.data_pipelines import EnhancedTextChunker, ProcessorConfig

# Create token-aware chunker
chunker = EnhancedTextChunker(
    config=ProcessorConfig(name="token_aware"),
    strategy="token_aware",
    chunk_size=4000,      # Target tokens (not characters!)
    overlap=200,          # Overlap in tokens
    max_tokens=8192,      # Hard limit
    encoding_name="cl100k_base"  # GPT-4 encoding
)

# Process document
result = await chunker.process(document)
```

## ⚙️ Configuration Options

### ChunkSplittingFilter

```python
filter = ChunkSplittingFilter(
    max_tokens=8192,           # Maximum tokens per chunk
    target_tokens=4000,        # Preferred chunk size
    overlap_tokens=200,        # Overlap between split chunks
    encoding_name="cl100k_base" # Tokenizer (GPT-4/3.5)
)
```

### TokenAwareChunker

```python
chunker = EnhancedTextChunker(
    strategy="token_aware",
    chunk_size=4000,           # Target tokens
    overlap=200,               # Overlap tokens
    max_tokens=8192,           # Hard limit
    encoding_name="cl100k_base", # Tokenizer
    preserve_sentences=True,   # Split at sentence boundaries
    preserve_paragraphs=True   # Split at paragraph boundaries
)
```

## 🔧 Encoding Options

Choose the right encoding for your LLM:

```python
# OpenAI GPT-4, GPT-3.5-turbo
encoding_name="cl100k_base"

# OpenAI GPT-3 (davinci, curie, etc.)
encoding_name="p50k_base"

# OpenAI Codex
encoding_name="p50k_base"
```

## 📊 Complete Example

```python
import asyncio
from gundy_ai.data_pipelines import (
    EnhancedDocumentProcessor,
    EnhancedTextChunker,
    ChunkSplittingFilter,
    ProcessorConfig
)

async def process_with_token_limits():
    # Step 1: Process document
    processor = EnhancedDocumentProcessor(
        config=ProcessorConfig(name="doc_processor")
    )

    doc_result = await processor.process("large_document.pdf")
    document = doc_result.data

    # Step 2: Create initial chunks
    chunker = EnhancedTextChunker(
        config=ProcessorConfig(name="initial_chunker"),
        strategy="structure_aware",
        chunk_size=4000
    )

    chunk_result = await chunker.process(document)
    chunked_doc = chunk_result.data

    # Step 3: Check for oversized chunks
    oversized = []
    for i, chunk in enumerate(chunked_doc.chunks):
        estimated_tokens = len(chunk.content) // 4  # Rough estimate
        if estimated_tokens > 8192:
            oversized.append((i, estimated_tokens))

    if oversized:
        print(f"Found {len(oversized)} oversized chunks")

        # Step 4: Apply chunk splitting
        filter = ChunkSplittingFilter(max_tokens=8192)
        final_doc = await filter.filter_document(chunked_doc)

        print(f"Split into {len(final_doc.chunks)} chunks")

        # Verify all chunks are within limits
        for chunk in final_doc.chunks:
            tokens = len(chunk.content) // 4
            assert tokens <= 8192, f"Chunk still too large: {tokens} tokens"

        return final_doc
    else:
        print("All chunks within limits")
        return chunked_doc

# Run the example
result = asyncio.run(process_with_token_limits())
```

## 🔍 Metadata and Tracking

Split chunks include metadata for tracking:

```python
for chunk in filtered_doc.chunks:
    if "split_from" in chunk.metadata:
        split_info = chunk.metadata
        print(f"Chunk {chunk.chunk_index}:")
        print(f"  Split from original chunk: {split_info['split_from']}")
        print(f"  Part {split_info['split_part']} of {split_info['split_total']}")
        print(f"  Split strategy: {split_info['split_strategy']}")
```

## 🎯 Best Practices

### 1. Choose Appropriate Target Sizes

```python
# Conservative (ensures room for prompts)
target_tokens=3000, max_tokens=8192

# Balanced (good utilization)
target_tokens=4000, max_tokens=8192

# Aggressive (maximum content per chunk)
target_tokens=6000, max_tokens=8192
```

### 2. Use Appropriate Overlap

```python
# Minimal overlap (more content, less redundancy)
overlap_tokens=100

# Balanced overlap (good context preservation)
overlap_tokens=200

# High overlap (maximum context preservation)
overlap_tokens=400
```

### 3. Preserve Structure When Possible

```python
# Enable structure preservation
preserve_sentences=True,
preserve_paragraphs=True

# This ensures splits happen at natural boundaries
# rather than mid-sentence or mid-paragraph
```

### 4. Monitor Split Statistics

```python
# Check splitting results
metadata = filter_result.metadata
print(f"Chunks split: {metadata.get('chunks_split', 0)}")
print(f"Average tokens: {metadata.get('avg_tokens_per_chunk', 0):.0f}")
print(f"Max tokens: {metadata.get('max_tokens_in_chunk', 0):.0f}")
```

## 🚨 Common Issues

### Issue 1: Still Getting Oversized Chunks

**Cause**: Very long sentences or paragraphs that can't be split naturally.

**Solution**: Disable structure preservation for problematic content:

```python
chunker = TokenAwareChunker(
    preserve_sentences=False,  # Allow mid-sentence splits
    preserve_paragraphs=False  # Allow mid-paragraph splits
)
```

### Issue 2: Too Many Small Chunks

**Cause**: Target token size too small or too much overlap.

**Solution**: Increase target size and reduce overlap:

```python
filter = ChunkSplittingFilter(
    target_tokens=6000,  # Larger target
    overlap_tokens=100   # Less overlap
)
```

### Issue 3: Encoding Errors

**Cause**: Wrong tokenizer for your LLM.

**Solution**: Use correct encoding:

```python
# For OpenAI GPT-4/3.5
encoding_name="cl100k_base"

# For older OpenAI models
encoding_name="p50k_base"
```

## 📈 Performance Impact

| Strategy            | Speed  | Accuracy | Memory | Use Case     |
| ------------------- | ------ | -------- | ------ | ------------ |
| Character splitting | Fast   | Low      | Low    | Last resort  |
| Sentence splitting  | Medium | High     | Medium | Balanced     |
| Paragraph splitting | Slow   | Highest  | High   | Best quality |

## 🎉 Integration with Existing Pipeline

The chunk splitting functionality integrates seamlessly with existing components:

```python
# Works with all chunking strategies
strategies = ["semantic", "structure_aware", "fixed_size"]

# Works with all output formats
output_formats = [OutputFormat.JSON, OutputFormat.NDJSON, OutputFormat.PARQUET]

# Works with audit logging
audit_hook = ProcessingAuditHook()

# Works with metrics collection
metrics_collector = MetricsCollector()
```

## 🚀 Ready to Use

The chunk splitting functionality is production-ready and includes:

- ✅ **Comprehensive error handling**
- ✅ **Detailed logging and metrics**
- ✅ **Multiple splitting strategies**
- ✅ **Configurable token limits**
- ✅ **Structure preservation options**
- ✅ **Full metadata tracking**

Start using it today to ensure your documents are compatible with any LLM token limits!
