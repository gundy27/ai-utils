# 🚀 Data Pipelines Library

**Enterprise-grade document processing and text chunking for AI applications**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

The `data_pipelines` library provides comprehensive document processing, intelligent text chunking, and pipeline orchestration capabilities optimized for AI applications, particularly RAG (Retrieval Augmented Generation) systems.

## ✨ Key Features

- **🔄 Unified Document Processing**: Single processor handles basic and advanced use cases
- **📄 Multi-Format Support**: PDF, DOCX, HTML, Markdown, and plain text
- **🧠 Smart Chunking**: Semantic, token-aware, and structure-aware chunking strategies
- **🎯 LLM Optimization**: Pre-configured settings for OpenAI, Claude, and local models
- **👁️ OCR Integration**: Automatic fallback for scanned documents
- **🧹 Text Cleaning**: Advanced cleaning for PDF artifacts and OCR errors
- **⚙️ Centralized Configuration**: Single configuration point for all components
- **🔌 Plugin System**: Extensible architecture for custom processing
- **📊 Observability**: Built-in metrics, audit logging, and monitoring
- **🚀 High Performance**: Async/await support with concurrent processing

## 🚀 Quick Start

### Installation

```bash
pip install "git+https://github.com/gundy27/ai-utils.git#subdirectory=libs/data_pipelines"
```

### One-Line Setup

```python
from gundy_ai.data_pipelines import quick_setup

# Instant setup for OpenAI GPT-4
processor = quick_setup("openai", "gpt-4")
result = await processor.process("document.pdf")
```

### Basic Usage

```python
import asyncio
from gundy_ai.data_pipelines import (
    DocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
    configure_for_openai,
    ChunkingStrategy,
)

async def process_document():
    # Configure for your LLM (do this once)
    configure_for_openai("gpt-4")

    # Create processor
    processor = DocumentProcessor(
        config=ProcessorConfig(name="my_processor")
    )

    # Process document
    doc_result = await processor.process("document.pdf")
    document = doc_result.data

    # Chunk the text
    chunker = EnhancedTextChunker(
        config=ProcessorConfig(name="chunker"),
        strategy=ChunkingStrategy.SEMANTIC
    )

    chunk_result = await chunker.process(document)
    chunks = chunk_result.data.chunks

    print(f"Processed {len(document.full_text)} characters into {len(chunks)} chunks")

# Run the example
asyncio.run(process_document())
```

## 🎯 LLM Configuration

The library provides optimized configurations for popular LLM providers:

```python
from gundy_ai.data_pipelines import (
    configure_for_openai,
    configure_for_claude,
    configure_for_local_llm,
)

# OpenAI GPT-4 (8,192 token limit)
configure_for_openai("gpt-4")

# Claude (100,000+ token limit)
configure_for_claude()

# Local model with custom context window
configure_for_local_llm(context_window=4096)
```

## 📄 Document Processing

### Basic Mode (Default)

Simple text extraction with minimal configuration:

```python
processor = DocumentProcessor(
    config=ProcessorConfig(name="basic_processor")
)
```

### Advanced Mode

Multiple parsers, OCR, and text cleaning:

```python
processor = DocumentProcessor(
    config=ProcessorConfig(name="advanced_processor"),
    pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf", "ocr_fallback"],
    enable_ocr_fallback=True,
    enable_text_cleaning=True,
    text_cleaning_strategy="auto"
)
```

### Supported Formats

- **PDF**: Multiple parsers (PyMuPDF, pdfplumber, PyPDF2) with OCR fallback
- **Word**: `.docx` and `.doc` files
- **Web**: HTML and HTM files
- **Markdown**: `.md` and `.markdown` files
- **Text**: Plain text files

## 🧩 Text Chunking Strategies

### Semantic Chunking

Groups text by meaning using embeddings:

```python
chunker = EnhancedTextChunker(
    config=ProcessorConfig(name="semantic_chunker"),
    strategy=ChunkingStrategy.SEMANTIC,
    chunk_size=1000
)
```

### Token-Aware Chunking

Optimized for LLM context windows:

```python
chunker = EnhancedTextChunker(
    config=ProcessorConfig(name="token_chunker"),
    strategy=ChunkingStrategy.TOKEN_AWARE
    # Automatically uses global configuration
)
```

### Structure-Aware Chunking

Preserves document hierarchy:

```python
chunker = EnhancedTextChunker(
    config=ProcessorConfig(name="structure_chunker"),
    strategy=ChunkingStrategy.STRUCTURE_AWARE,
    chunk_size=800
)
```

### Chunk Splitting

Handle oversized chunks automatically:

```python
from gundy_ai.data_pipelines import ChunkSplittingFilter

# Split chunks that exceed token limits
splitter = ChunkSplittingFilter()
final_doc = await splitter.filter_document(chunked_doc)
```

## ⚙️ Configuration System

### Global Configuration

Set once, use everywhere:

```python
from gundy_ai.data_pipelines import ChunkingConfig, ProcessingConfig, set_config

config = ProcessingConfig(
    chunking=ChunkingConfig(
        max_tokens=8192,
        target_tokens=4000,
        overlap_tokens=200
    )
)
set_config(config)

# All components now use these settings
```

### Environment Variables

Configure via environment:

```bash
export CHUNKING_MAX_TOKENS=8192
export CHUNKING_TARGET_TOKENS=4000
export ENABLE_OCR_FALLBACK=true
export ENABLE_TEXT_CLEANING=true
```

### Component-Level Overrides

Override global settings when needed:

```python
chunker = EnhancedTextChunker(
    config=ProcessorConfig(name="custom_chunker"),
    chunk_size=2000,  # Override global setting
    strategy=ChunkingStrategy.SEMANTIC
)
```

## 🔌 Advanced Features

### OCR Integration

Automatic OCR for scanned documents:

```python
processor = DocumentProcessor(
    config=ProcessorConfig(name="ocr_processor"),
    enable_ocr_fallback=True,
    ocr_confidence_threshold=0.7,
    min_text_extraction_ratio=0.1
)
```

### Text Cleaning

Remove artifacts and normalize text:

```python
processor = DocumentProcessor(
    config=ProcessorConfig(name="cleaning_processor"),
    enable_text_cleaning=True,
    text_cleaning_strategy="auto"  # or "pdf", "ocr", "general"
)
```

### Output Formats

Multiple output formats supported:

```python
from gundy_ai.data_pipelines.output_formats import OutputManager, OutputFormat

output_manager = OutputManager()
await output_manager.write_document(
    document=processed_doc,
    output_format=OutputFormat.PARQUET,
    output_path="output.parquet"
)
```

### Plugin System

Extend functionality with custom plugins:

```python
from gundy_ai.data_pipelines.plugins import PluginManager

plugin_manager = PluginManager()
plugin_manager.register_parser("custom_parser", MyCustomParser())
```

### Metrics and Observability

Built-in monitoring and metrics:

```python
from gundy_ai.data_pipelines.metrics import MetricsCollector

collector = MetricsCollector()
# Metrics are automatically collected during processing
report = collector.generate_report()
```

## 📊 Performance

| Strategy          | Speed  | Memory    | Accuracy   | Use Case         |
| ----------------- | ------ | --------- | ---------- | ---------------- |
| Fixed Size        | ⚡⚡⚡ | 🟢 Low    | 🟡 Medium  | Simple documents |
| Sentence Boundary | ⚡⚡   | 🟢 Low    | 🟢 High    | General purpose  |
| Semantic          | ⚡     | 🟡 Medium | 🟢 Highest | RAG systems      |
| Token-Aware       | ⚡⚡   | 🟢 Low    | 🟢 High    | LLM optimization |

## 🛠️ CLI Usage

Process documents from the command line:

```bash
# Basic processing
python -m gundy_ai.data_pipelines.cli process document.pdf --output chunks.json

# Advanced processing with OCR
python -m gundy_ai.data_pipelines.cli process document.pdf \
    --strategy semantic \
    --chunk-size 1000 \
    --enable-ocr \
    --output-format parquet
```

## 📚 Examples

The library includes comprehensive examples:

- **`quick_start_guide.py`** - Simplified API demonstration
- **`basic_usage.py`** - Basic document processing
- **`advanced_pdf_demo.py`** - PDF processing with OCR and multiple parsers
- **`advanced_chunking_demo.py`** - All chunking strategies with comparisons
- **`centralized_config_demo.py`** - Configuration system usage
- **`comprehensive_processing_demo.py`** - End-to-end pipeline
- **`metrics_demo.py`** - Observability and monitoring
- **`output_formats_demo.py`** - Different output formats
- **`plugin_system_demo.py`** - Plugin system usage

## 🔧 Advanced Usage

### Custom Processing Pipeline

```python
from gundy_ai.data_pipelines import DataPipeline, PipelineStage

pipeline = DataPipeline([
    PipelineStage("document", DocumentProcessor(config)),
    PipelineStage("chunking", EnhancedTextChunker(config)),
    PipelineStage("embedding", EmbeddingProcessor(config)),
])

result = await pipeline.process("document.pdf")
```

### Batch Processing

```python
import asyncio
from pathlib import Path

async def process_directory(directory: Path):
    processor = quick_setup("openai", "gpt-4")

    tasks = []
    for file_path in directory.glob("*.pdf"):
        tasks.append(processor.process(str(file_path)))

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Custom Configuration

```python
from gundy_ai.data_pipelines import ChunkingConfig, ProcessingConfig

custom_config = ProcessingConfig(
    chunking=ChunkingConfig(
        max_tokens=6000,
        target_tokens=3000,
        overlap_tokens=300,
        semantic_similarity_threshold=0.8
    ),
    enable_ocr_fallback=True,
    ocr_confidence_threshold=0.8,
    enable_text_cleaning=True
)

set_config(custom_config)
```

## 🚨 Migration Guide

### From EnhancedDocumentProcessor

```python
# Old way
from gundy_ai.data_pipelines import EnhancedDocumentProcessor

processor = EnhancedDocumentProcessor(config, ...)

# New way (EnhancedDocumentProcessor still works but is deprecated)
from gundy_ai.data_pipelines import DocumentProcessor

processor = DocumentProcessor(
    config=config,
    pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf"],
    enable_ocr_fallback=True,
    enable_text_cleaning=True
)
```

### From Manual Configuration

```python
# Old way - configure each component separately
chunker1 = EnhancedTextChunker(chunk_size=4000, overlap=200)
chunker2 = EnhancedTextChunker(chunk_size=4000, overlap=200)

# New way - configure once, use everywhere
configure_for_openai("gpt-4")
chunker1 = EnhancedTextChunker(config=ProcessorConfig(name="chunker1"))
chunker2 = EnhancedTextChunker(config=ProcessorConfig(name="chunker2"))
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and examples
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- **Documentation**: Check the `examples/` directory for detailed usage examples
- **Issues**: Report bugs and request features on GitHub
- **Configuration**: Use the built-in configuration presets for common LLM providers

## 🎯 Roadmap

- [ ] Additional document formats (PowerPoint, Excel)
- [ ] More embedding model integrations
- [ ] Advanced semantic search capabilities
- [ ] Real-time document processing
- [ ] Cloud storage integrations
- [ ] Performance optimizations

---

**Built with ❤️ for the AI community**
