# Configuration Guide

The `data_pipelines` library provides a centralized configuration system that makes it easy to adjust chunk sizes and other processing settings across all components.

## 🎯 Quick Start

### Configure for Popular LLMs

```python
from gundy_ai.data_pipelines import configure_for_openai, configure_for_claude, configure_for_local_llm

# OpenAI GPT-4 (8,192 token limit)
configure_for_openai("gpt-4")

# OpenAI GPT-3.5-turbo (8,192 token limit)
configure_for_openai("gpt-3.5-turbo")

# Claude (100,000+ token limit)
configure_for_claude()

# Local model with 4K context window
configure_for_local_llm(4096)

# Local model with 16K context window
configure_for_local_llm(16384)
```

### Use Pre-configured Settings

```python
from gundy_ai.data_pipelines import (
    OPENAI_GPT4_CONFIG,
    OPENAI_GPT35_CONFIG,
    CLAUDE_CONFIG,
    LOCAL_4K_CONFIG,
    LOCAL_8K_CONFIG,
    LOCAL_16K_CONFIG,
    set_config
)

# Apply a preset configuration
set_config(OPENAI_GPT4_CONFIG)
```

## ⚙️ Configuration Options

### ChunkingConfig

Controls how text is split into chunks:

```python
from gundy_ai.data_pipelines import ChunkingConfig, ProcessingConfig, set_config

chunking_config = ChunkingConfig(
    # Token-based settings (for LLM compatibility)
    max_tokens=8192,          # Hard limit (OpenAI GPT-4/3.5)
    target_tokens=4000,       # Preferred chunk size
    overlap_tokens=200,       # Overlap between chunks

    # Character-based settings (fallback/legacy)
    max_chunk_size=4000,      # Maximum characters per chunk
    min_chunk_size=100,       # Minimum characters per chunk
    overlap_size=200,         # Character overlap

    # Tokenizer settings
    encoding_name="cl100k_base",  # GPT-4/3.5 encoding

    # Structure preservation
    preserve_sentences=True,
    preserve_paragraphs=True,

    # Strategy-specific settings
    semantic_similarity_threshold=0.7,
    structure_aware_min_section_size=50,
)

# Apply the configuration
config = ProcessingConfig(chunking=chunking_config)
set_config(config)
```

### ProcessingConfig

Controls overall document processing behavior:

```python
from gundy_ai.data_pipelines import ProcessingConfig, ChunkingConfig

config = ProcessingConfig(
    # Chunking configuration
    chunking=ChunkingConfig(...),

    # PDF processing
    pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf", "ocr_fallback"],
    enable_ocr_fallback=True,
    ocr_confidence_threshold=0.6,
    min_text_extraction_ratio=0.1,

    # Text cleaning
    enable_text_cleaning=True,
    text_cleaning_strategy="auto",

    # Output settings
    default_output_format="json",
    include_metadata=True,

    # Performance settings
    max_concurrent_operations=10,
    timeout_seconds=300,
)

set_config(config)
```

## 🌍 Environment Variables

Configure the library using environment variables:

```bash
# Token limits
export CHUNKING_MAX_TOKENS=8192
export CHUNKING_TARGET_TOKENS=4000
export CHUNKING_OVERLAP_TOKENS=200

# Character limits (fallback)
export CHUNKING_MAX_CHUNK_SIZE=4000
export CHUNKING_MIN_CHUNK_SIZE=100
export CHUNKING_OVERLAP_SIZE=200

# Tokenizer
export CHUNKING_ENCODING=cl100k_base

# Structure preservation
export CHUNKING_PRESERVE_SENTENCES=true
export CHUNKING_PRESERVE_PARAGRAPHS=true

# Processing settings
export ENABLE_OCR_FALLBACK=true
export OCR_CONFIDENCE_THRESHOLD=0.6
export ENABLE_TEXT_CLEANING=true
export DEFAULT_OUTPUT_FORMAT=json
```

Then create configuration from environment:

```python
from gundy_ai.data_pipelines import ProcessingConfig, set_config

config = ProcessingConfig.from_env()
set_config(config)
```

## 🎯 Configuration Hierarchy

The configuration system follows this hierarchy (highest to lowest priority):

1. **Explicit parameters** passed to components
2. **Custom ChunkingConfig** passed to components
3. **Global configuration** set via `set_config()`
4. **Environment variables**
5. **Default values**

### Example: Component-Level Overrides

```python
from gundy_ai.data_pipelines import (
    configure_for_openai,
    EnhancedTextChunker,
    ProcessorConfig,
    ChunkingConfig
)

# Set global configuration
configure_for_openai("gpt-4")  # 4000 target tokens

# Chunker using global config
global_chunker = EnhancedTextChunker(
    config=ProcessorConfig(name="global"),
    strategy="token_aware"
    # Uses global 4000 target tokens
)

# Chunker with parameter override
override_chunker = EnhancedTextChunker(
    config=ProcessorConfig(name="override"),
    strategy="token_aware",
    chunk_size=2000  # Override to 2000 tokens
)

# Chunker with custom config
custom_config = ChunkingConfig(
    max_tokens=6000,
    target_tokens=3000,
    overlap_tokens=150
)

custom_chunker = EnhancedTextChunker(
    config=ProcessorConfig(name="custom"),
    strategy="token_aware",
    chunking_config=custom_config  # Uses custom config
)
```

## 🔧 Common Use Cases

### 1. Switch Between LLM Providers

```python
from gundy_ai.data_pipelines import configure_for_openai, configure_for_claude

# Processing for OpenAI
configure_for_openai("gpt-4")
# ... process documents ...

# Switch to Claude for larger context
configure_for_claude()
# ... process documents with larger chunks ...
```

### 2. Handle Oversized Chunks

```python
from gundy_ai.data_pipelines import ChunkSplittingFilter, get_config

# Process document with any chunker
chunked_doc = await chunker.process(document)

# Check for oversized chunks
max_tokens = get_config().chunking.max_tokens
oversized = [
    (i, len(chunk.content) // 4)
    for i, chunk in enumerate(chunked_doc.chunks)
    if len(chunk.content) // 4 > max_tokens
]

if oversized:
    # Split oversized chunks (uses global config automatically)
    filter = ChunkSplittingFilter()
    final_doc = await filter.filter_document(chunked_doc)
```

### 3. Development vs Production Settings

```python
import os
from gundy_ai.data_pipelines import ProcessingConfig, set_config

if os.getenv("ENVIRONMENT") == "production":
    # Production: Optimize for throughput
    config = ProcessingConfig.for_llm("openai", "gpt-4")
    config.max_concurrent_operations = 20
    config.timeout_seconds = 600
else:
    # Development: Smaller chunks for testing
    config = ProcessingConfig.for_llm("local", "4096")
    config.max_concurrent_operations = 5
    config.timeout_seconds = 120

set_config(config)
```

## 📊 Configuration Inspection

```python
from gundy_ai.data_pipelines import get_config

# Get current configuration
config = get_config()

print(f"Max tokens: {config.chunking.max_tokens}")
print(f"Target tokens: {config.chunking.target_tokens}")
print(f"Overlap: {config.chunking.overlap_tokens}")
print(f"Encoding: {config.chunking.encoding_name}")
print(f"OCR enabled: {config.enable_ocr_fallback}")
```

## 🔄 Reset Configuration

```python
from gundy_ai.data_pipelines import reset_config

# Reset to default values
reset_config()
```

## 💡 Best Practices

1. **Set configuration early** in your application startup
2. **Use LLM-specific presets** when possible for optimal performance
3. **Override at component level** only when necessary
4. **Use environment variables** for deployment-specific settings
5. **Test with different configurations** to find optimal chunk sizes
6. **Monitor chunk sizes** in production to ensure they stay within limits

## 🚀 Migration from Manual Configuration

If you were previously setting chunk sizes manually:

```python
# Old way - manual configuration everywhere
chunker1 = EnhancedTextChunker(chunk_size=4000, overlap=200)
chunker2 = EnhancedTextChunker(chunk_size=4000, overlap=200)
filter = ChunkSplittingFilter(max_tokens=8192, target_tokens=4000)

# New way - centralized configuration
from gundy_ai.data_pipelines import configure_for_openai

configure_for_openai("gpt-4")  # Sets defaults for all components

chunker1 = EnhancedTextChunker()  # Uses global config
chunker2 = EnhancedTextChunker()  # Uses global config
filter = ChunkSplittingFilter()   # Uses global config
```

This ensures consistency and makes it easy to adjust settings globally!
