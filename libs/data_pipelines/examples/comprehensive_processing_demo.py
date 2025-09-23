"""Comprehensive demo of enhanced data pipelines features."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.data_pipelines import (
    EnhancedDocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
)


async def main():
    """Demonstrate comprehensive document processing pipeline."""
    print("🚀 Comprehensive Data Pipelines Demo")
    print("=" * 60)

    # Sample document with various challenges
    sample_text = """
# Advanced PDF Processing and Text Analysis

This document demonstrates the enhanced capabilities of the data pipelines library, including multiple PDF parsing strategies, advanced text cleaning, and semantic chunking.

## PDF Parsing Strategies

### PDFPlumber Parser
PDFPlumber excels at preserving document layout and extracting tables. It's particularly effective for multi-column documents and complex layouts. The parser maintains spatial relationships between text elements.

### PyMuPDF Parser  
PyMuPDF (fitz) offers high-performance processing with detailed formatting information. It can extract images, links, and provides precise positioning data for all text elements.

### OCR Fallback
When traditional PDF parsing fails or produces poor results, the system automatically falls back to OCR using Tesseract. This is essential for scanned documents or PDFs with embedded images.

## Text Cleaning Capabilities

The enhanced text cleaning system addresses common issues:

- **Header/Footer Removal**: Automatically detects and removes repeated headers and footers
- **OCR Artifact Cleanup**: Fixes common OCR errors like character substitutions
- **Encoding Issues**: Resolves Unicode and encoding problems
- **Whitespace Normalization**: Standardizes spacing while preserving structure

## Semantic Chunking

Traditional fixed-size chunking can break semantic coherence. Our semantic chunking strategy:

1. Splits text into sentences
2. Generates embeddings for each sentence
3. Groups semantically similar sentences together
4. Respects token limits while maintaining coherence

This approach is particularly valuable for retrieval-augmented generation (RAG) systems where semantic coherence is crucial for accurate question answering.

## Structure-Aware Chunking

For documents with clear hierarchical structure, structure-aware chunking:

- Preserves heading-content relationships
- Maintains section boundaries
- Keeps related paragraphs together
- Provides metadata about document structure

## Integration with Audit System

All processing operations are tracked through the audit system, providing:

- Detailed processing statistics
- Parser selection rationale
- Performance metrics
- Error tracking and recovery

## Conclusion

These enhancements make the data pipelines library suitable for production RAG systems, document analysis platforms, and knowledge management applications.
    """

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(sample_text)
        temp_file = f.name

    try:
        print("📄 Processing comprehensive document...")
        print()

        # Initialize enhanced document processor
        doc_config = ProcessorConfig(name="comprehensive_demo")
        doc_processor = EnhancedDocumentProcessor(
            config=doc_config,
            pdf_parser_priority=["pdfplumber", "pymupdf", "pypdf"],
            enable_ocr_fallback=True,
            enable_text_cleaning=True,
            text_cleaning_strategy="auto",
        )

        # Process document
        doc_result = await doc_processor.process(temp_file)

        if not doc_result.success:
            print(f"❌ Document processing failed: {doc_result.error}")
            return

        document = doc_result.data
        metadata = document.metadata.custom_metadata

        print("✅ Document Processing Results:")
        print(f"   📊 Text length: {len(document.full_text):,} characters")
        print(f"   📄 Word count: {document.metadata.word_count:,}")
        print(f"   🔧 Text cleaning: {metadata.get('text_cleaning_enabled', False)}")
        print(
            f"   📈 Processing time: {doc_result.metadata.get('processing_time_ms', 0):.1f}ms"
        )
        print()

        # Test different chunking strategies
        chunking_strategies = [
            {
                "name": "semantic",
                "title": "🧠 Semantic Chunking",
                "config": {
                    "strategy": "semantic",
                    "chunk_size": 600,
                    "model_name": "all-MiniLM-L6-v2",
                    "similarity_threshold": 0.75,
                },
            },
            {
                "name": "structure_aware",
                "title": "🏗️  Structure-Aware Chunking",
                "config": {
                    "strategy": "structure_aware",
                    "chunk_size": 600,
                    "preserve_headings": True,
                    "preserve_paragraphs": True,
                },
            },
            {
                "name": "fixed_size",
                "title": "📏 Fixed-Size Chunking (Baseline)",
                "config": {"strategy": "fixed_size", "chunk_size": 600, "overlap": 100},
            },
        ]

        results = {}

        for strategy_info in chunking_strategies:
            name = strategy_info["name"]
            title = strategy_info["title"]
            config = strategy_info["config"]

            print(title)
            print("-" * 50)

            # Initialize chunker
            chunker_config = ProcessorConfig(name=f"chunker_{name}")
            chunker = EnhancedTextChunker(config=chunker_config, **config)

            # Chunk the document
            chunk_result = await chunker.process(document)

            if chunk_result.success:
                chunked_doc = chunk_result.data
                chunks = chunked_doc.chunks

                # Calculate statistics
                token_counts = [chunk.token_count for chunk in chunks]
                avg_tokens = (
                    sum(token_counts) / len(token_counts) if token_counts else 0
                )

                results[name] = {
                    "chunks": len(chunks),
                    "avg_tokens": avg_tokens,
                    "token_range": (
                        (min(token_counts), max(token_counts))
                        if token_counts
                        else (0, 0)
                    ),
                    "processing_time": chunk_result.metadata.get(
                        "processing_time_ms", 0
                    ),
                }

                print(f"✅ Created {len(chunks)} chunks")
                print(f"   📊 Average tokens: {avg_tokens:.1f}")
                print(f"   📊 Token range: {min(token_counts)} - {max(token_counts)}")
                print(
                    f"   ⏱️  Processing time: {chunk_result.metadata.get('processing_time_ms', 0):.1f}ms"
                )

                # Show sample chunks
                print("   📝 Sample chunks:")
                for i, chunk in enumerate(chunks[:2]):
                    preview = (
                        chunk.content[:120] + "..."
                        if len(chunk.content) > 120
                        else chunk.content
                    )
                    print(f"      Chunk {i+1}: {repr(preview)}")

                    # Show strategy-specific metadata
                    if name == "semantic" and "avg_similarity" in chunk.metadata:
                        print(
                            f"         Semantic similarity: {chunk.metadata['avg_similarity']:.3f}"
                        )
                    elif (
                        name == "structure_aware"
                        and "primary_heading" in chunk.metadata
                    ):
                        print(f"         Section: {chunk.metadata['primary_heading']}")

                print()
            else:
                print(f"❌ Chunking failed: {chunk_result.error}")
                print()

        # Comparison summary
        print("📊 Strategy Comparison:")
        print("-" * 50)
        for name, stats in results.items():
            print(
                f"{name.replace('_', ' ').title():20} | "
                f"Chunks: {stats['chunks']:2d} | "
                f"Avg Tokens: {stats['avg_tokens']:5.1f} | "
                f"Time: {stats['processing_time']:5.1f}ms"
            )
        print()

        print("🎯 Key Benefits:")
        print("   • Multiple PDF parsing strategies with automatic fallback")
        print("   • Advanced text cleaning for better quality")
        print("   • Semantic chunking preserves meaning")
        print("   • Structure-aware chunking maintains hierarchy")
        print("   • Comprehensive metadata and performance tracking")
        print()

        print("💡 Production Use Cases:")
        print("   • RAG systems requiring high-quality chunks")
        print("   • Document analysis and knowledge extraction")
        print("   • Multi-format document processing pipelines")
        print("   • Enterprise content management systems")

    finally:
        # Cleanup
        Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
