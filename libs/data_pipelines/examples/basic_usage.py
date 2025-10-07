"""Basic usage example for data pipelines."""

import asyncio
import os
from pathlib import Path

from gundy_ai.data_pipelines import (
    create_default_document_pipeline,
    DocumentProcessor,
    TextChunker,
    ProcessorConfig,
    ChunkingStrategy,
)


async def example_basic_pipeline():
    """Example of using the default document processing pipeline."""
    print("=== Basic Pipeline Example ===")

    # Check if OpenAI API key is available
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set. This example will fail without it.")
        print("   Set your API key: export OPENAI_API_KEY=your_key_here")
        return

    # Create pipeline configuration
    embedding_config = {
        "model": "text-embedding-3-small",
        "api_key": api_key,
        "max_batch_size": 10,  # Small batch for demo
    }

    # Create pipeline
    pipeline = create_default_document_pipeline(
        embedding_config=embedding_config,
        chunk_size=500,  # Small chunks for demo
        chunk_overlap=100,
    )

    # Create a sample text file for processing
    sample_text = """
    This is a sample document for demonstrating the data processing pipeline.
    
    The pipeline can extract text from various document formats including PDF, DOCX, HTML, and plain text.
    It then chunks the text into smaller pieces for better processing and generates embeddings for each chunk.
    
    This enables efficient search and retrieval of information from large document collections.
    The embeddings can be used with vector databases for semantic search capabilities.
    
    The pipeline supports multiple chunking strategies including fixed size, sentence boundary, and paragraph boundary.
    It also includes retry logic and error handling for robust processing.
    """

    sample_file = Path("sample_document.txt")
    sample_file.write_text(sample_text)

    try:
        print(f"Processing document: {sample_file}")

        # Process the document
        result = await pipeline.process_documents([str(sample_file)])

        print("\nResults:")
        print(f"  Successfully processed: {result.processed_count}")
        print(f"  Failed: {result.failed_count}")
        print(f"  Success rate: {result.get_success_rate():.1f}%")
        print(f"  Execution time: {result.execution_time_ms}ms")

        # Show detailed results
        for i, processing_result in enumerate(result.results):
            if processing_result.success:
                embedded_doc = processing_result.data

                print(f"\nDocument {i+1}:")
                print(f"  Filename: {embedded_doc.document.metadata.filename}")
                print(
                    f"  Document type: {embedded_doc.document.metadata.document_type.value}"
                )
                print(f"  Word count: {embedded_doc.document.metadata.word_count}")
                print(f"  Chunks created: {embedded_doc.get_embedding_count()}")
                print(f"  Total tokens: {embedded_doc.get_total_embeddings_tokens()}")

                # Show first chunk as example
                if embedded_doc.document.chunks:
                    first_chunk = embedded_doc.document.chunks[0]
                    print("\n  First chunk:")
                    print(f"    Content: {first_chunk.content[:100]}...")
                    print(f"    Tokens: {first_chunk.token_count}")
                    print(
                        f"    Position: {first_chunk.start_char}-{first_chunk.end_char}"
                    )

                # Show embedding info
                if embedded_doc.embeddings:
                    first_embedding = embedded_doc.embeddings[0]
                    print("\n  First embedding:")
                    print(f"    Model: {first_embedding.model}")
                    print(f"    Dimensions: {len(first_embedding.vector)}")
                    print(f"    Token count: {first_embedding.token_count}")
            else:
                print(f"\nDocument {i+1} failed: {processing_result.error}")

    finally:
        # Clean up sample file
        if sample_file.exists():
            sample_file.unlink()


async def example_individual_components():
    """Example of using individual pipeline components."""
    print("\n=== Individual Components Example ===")

    # Create processors
    # Basic mode (default) - simple text extraction
    doc_processor = DocumentProcessor(
        ProcessorConfig(name="document_processor", max_retries=2, timeout_seconds=60)
    )

    # Advanced mode example (uncomment to enable):
    # doc_processor = DocumentProcessor(
    #     ProcessorConfig(name="document_processor", max_retries=2, timeout_seconds=60),
    #     pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf"],
    #     enable_ocr_fallback=True,
    #     enable_text_cleaning=True
    # )

    chunker = TextChunker(
        ProcessorConfig(name="text_chunker", max_retries=2, timeout_seconds=30),
        strategy=ChunkingStrategy.SENTENCE_BOUNDARY,
        chunk_size=300,
        overlap=50,
    )

    # Create sample text file
    sample_text = """
    This is another sample document for demonstrating individual components.
    
    The document processor can extract text from various formats.
    The text chunker can split text using different strategies.
    The embedding processor can generate vector embeddings for text chunks.
    
    Each component can be used independently or combined in custom pipelines.
    """

    sample_file = Path("sample_components.txt")
    sample_file.write_text(sample_text)

    try:
        print(f"Processing with individual components: {sample_file}")

        # Step 1: Extract text from document
        print("\n1. Extracting text from document...")
        doc_result = await doc_processor.process_with_retry(str(sample_file))

        if not doc_result.success:
            print(f"Document processing failed: {doc_result.error}")
            return

        processed_doc = doc_result.data
        print(f"   Extracted {len(processed_doc.full_text)} characters")
        print(f"   Document type: {processed_doc.metadata.document_type.value}")

        # Step 2: Chunk the text
        print("\n2. Chunking text...")
        chunk_result = await chunker.process_with_retry(processed_doc)

        if not chunk_result.success:
            print(f"Text chunking failed: {chunk_result.error}")
            return

        chunked_doc = chunk_result.data
        print(f"   Created {len(chunked_doc.chunks)} chunks")

        # Show chunk details
        for i, chunk in enumerate(chunked_doc.chunks[:3]):  # Show first 3 chunks
            print(
                f"   Chunk {i+1}: {chunk.token_count} tokens, {chunk.start_char}-{chunk.end_char} chars"
            )
            print(f"             Content: {chunk.content[:80]}...")

        if len(chunked_doc.chunks) > 3:
            print(f"   ... and {len(chunked_doc.chunks) - 3} more chunks")

    finally:
        # Clean up sample file
        if sample_file.exists():
            sample_file.unlink()


async def example_chunking_strategies():
    """Example demonstrating different chunking strategies."""
    print("\n=== Chunking Strategies Example ===")

    sample_text = """
    This document demonstrates different text chunking strategies.
    
    Fixed size chunking splits text into chunks of a specific token count.
    This ensures consistent chunk sizes but may split sentences or paragraphs.
    
    Sentence boundary chunking splits text at sentence boundaries.
    This preserves sentence integrity but may result in varying chunk sizes.
    
    Paragraph boundary chunking splits text at paragraph boundaries.
    This preserves paragraph structure and is good for document-level processing.
    """

    sample_file = Path("sample_chunking.txt")
    sample_file.write_text(sample_text)

    try:
        doc_processor = DocumentProcessor(ProcessorConfig(name="doc_processor"))

        # Extract text first
        doc_result = await doc_processor.process_with_retry(str(sample_file))
        if not doc_result.success:
            print(f"Document processing failed: {doc_result.error}")
            return

        processed_doc = doc_result.data

        # Test different chunking strategies
        strategies = [
            (ChunkingStrategy.FIXED_SIZE, "Fixed Size"),
            (ChunkingStrategy.SENTENCE_BOUNDARY, "Sentence Boundary"),
            (ChunkingStrategy.PARAGRAPH_BOUNDARY, "Paragraph Boundary"),
        ]

        for strategy, name in strategies:
            print(f"\n{name} Chunking:")

            chunker = TextChunker(
                ProcessorConfig(name=f"chunker_{strategy.value}"),
                strategy=strategy,
                chunk_size=200,
                overlap=50,
            )

            result = await chunker.process_with_retry(processed_doc)

            if result.success:
                chunked_doc = result.data
                print(f"  Created {len(chunked_doc.chunks)} chunks")

                for i, chunk in enumerate(chunked_doc.chunks):
                    print(f"  Chunk {i+1}: {chunk.token_count} tokens")
                    print(f"           Content: {chunk.content[:60]}...")
            else:
                print(f"  Failed: {result.error}")

    finally:
        # Clean up sample file
        if sample_file.exists():
            sample_file.unlink()


async def main():
    """Run all examples."""
    print("Data Pipelines Examples")
    print("=" * 50)

    # Run examples
    await example_basic_pipeline()
    await example_individual_components()
    await example_chunking_strategies()

    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
