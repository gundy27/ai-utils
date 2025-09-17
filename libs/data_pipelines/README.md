# gundy-ai-data-pipelines

Data processing utilities for AI applications, providing document extraction, text chunking, and embedding generation capabilities.

## Features

- **Document Processing**: Extract text from PDF, DOCX, HTML, Markdown, and plain text files
- **Text Chunking**: Multiple chunking strategies (fixed size, sentence boundary, paragraph boundary)
- **Embedding Generation**: Integration with OpenAI embedding models
- **Pipeline Orchestration**: Configurable processing pipelines with retry logic
- **CLI Interface**: Command-line tools for batch processing
- **Async Support**: Full async/await support for high-performance processing

## Installation

```bash
pip install "git+https://github.com/gundy27/ai-utils.git#subdirectory=libs/data_pipelines"
```

## Quick Start

### Basic Usage

```python
import asyncio
from gundy_ai.data_pipelines import (
    create_default_document_pipeline,
    EmbeddingConfig,
    EmbeddingModel
)

async def process_documents():
    # Create pipeline configuration
    embedding_config = {
        "model": "text-embedding-3-small",
        "api_key": "your-openai-api-key",
        "max_batch_size": 100
    }

    # Create pipeline
    pipeline = create_default_document_pipeline(
        embedding_config=embedding_config,
        chunk_size=1000,
        chunk_overlap=200
    )

    # Process documents
    file_paths = ["document1.pdf", "document2.docx"]
    result = await pipeline.process_documents(file_paths)

    print(f"Processed {result.processed_count} documents")
    print(f"Success rate: {result.get_success_rate():.1f}%")

# Run the processing
asyncio.run(process_documents())
```

### Individual Components

```python
from gundy_ai.data_pipelines import (
    DocumentProcessor,
    TextChunker,
    EmbeddingProcessor,
    ProcessorConfig,
    EmbeddingConfig,
    EmbeddingModel
)

# Document processing
doc_processor = DocumentProcessor(
    ProcessorConfig(name="doc_processor")
)

# Text chunking
chunker = TextChunker(
    ProcessorConfig(name="chunker"),
    chunk_size=1000,
    overlap=200
)

# Embedding generation
embedding_processor = EmbeddingProcessor(
    ProcessorConfig(name="embedder"),
    EmbeddingConfig(
        model=EmbeddingModel.OPENAI_TEXT_EMBEDDING_3_SMALL,
        api_key="your-api-key"
    )
)
```

## CLI Usage

### Process Documents

```bash
# Process a single document
data-pipeline process-documents document.pdf --api-key YOUR_API_KEY

# Process a directory of documents
data-pipeline process-documents ./documents/ --output ./results/

# Customize processing parameters
data-pipeline process-documents ./docs/ \
    --model text-embedding-3-large \
    --chunk-size 1500 \
    --chunk-overlap 300 \
    --batch-size 50 \
    --max-concurrent 3
```

### Generate Embeddings

```bash
# Generate embeddings for a text file
data-pipeline generate-embeddings text.txt --output embeddings.json
```

## Configuration

### Embedding Models

Supported embedding models:

- `text-embedding-3-small` (default)
- `text-embedding-3-large`
- `text-embedding-ada-002`

### Chunking Strategies

- **Fixed Size**: Split text into fixed token count chunks
- **Sentence Boundary**: Split at sentence boundaries
- **Paragraph Boundary**: Split at paragraph boundaries

### Pipeline Configuration

```python
from gundy_ai.data_pipelines import PipelineConfig, PipelineStage

config = PipelineConfig(
    name="my_pipeline",
    stages=[
        PipelineStage.DOCUMENT_EXTRACTION,
        PipelineStage.TEXT_CHUNKING,
        PipelineStage.EMBEDDING_GENERATION
    ],
    max_concurrent_documents=5,
    retry_failed_stages=True
)
```

## Supported Document Types

- **Text**: `.txt` files
- **PDF**: `.pdf` files
- **Word**: `.docx`, `.doc` files
- **HTML**: `.html`, `.htm` files
- **Markdown**: `.md`, `.markdown` files

## Error Handling

The library includes comprehensive error handling:

- **Retry Logic**: Automatic retry with exponential backoff
- **Timeout Protection**: Configurable timeouts for each stage
- **Validation**: Input validation at each processing stage
- **Detailed Logging**: Structured logging with context

## Performance

- **Async Processing**: Full async/await support
- **Batch Processing**: Process multiple documents concurrently
- **Memory Efficient**: Streaming processing for large documents
- **Configurable Concurrency**: Control resource usage

## Examples

### Custom Pipeline

```python
from gundy_ai.data_pipelines import (
    DataPipeline,
    PipelineConfig,
    PipelineStage
)

# Create custom pipeline
config = PipelineConfig(
    name="custom_pipeline",
    stages=[
        PipelineStage.DOCUMENT_EXTRACTION,
        PipelineStage.TEXT_CHUNKING,
        PipelineStage.EMBEDDING_GENERATION
    ]
)

pipeline = DataPipeline(config)

# Add custom processors
pipeline.add_stage(PipelineStage.DOCUMENT_EXTRACTION, doc_processor)
pipeline.add_stage(PipelineStage.TEXT_CHUNKING, chunker)
pipeline.add_stage(PipelineStage.EMBEDDING_GENERATION, embedding_processor)

# Process documents
result = await pipeline.process_batch(file_paths)
```

### Processing Results

```python
# Access processing results
for result in pipeline_result.results:
    if result.success:
        embedded_doc = result.data

        print(f"Document: {embedded_doc.document.metadata.filename}")
        print(f"Chunks: {embedded_doc.get_embedding_count()}")
        print(f"Tokens: {embedded_doc.get_total_embeddings_tokens()}")

        # Access individual chunks and embeddings
        for i, (chunk, embedding) in enumerate(
            zip(embedded_doc.document.chunks, embedded_doc.embeddings)
        ):
            print(f"Chunk {i}: {len(embedding.vector)} dimensions")
```

## Integration

This library integrates seamlessly with other components in the ai-utils ecosystem:

- **Auth Service**: Secure API key management
- **API Service Starter**: Use in FastAPI applications
- **REST Client**: HTTP-based embedding services

## License

Part of the gundy-ai-utils project. See main repository for license information.
