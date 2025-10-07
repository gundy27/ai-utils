"""Quick start guide showing the simplified API for common use cases."""

import asyncio
import tempfile
from pathlib import Path

# Simple imports - everything you need for most use cases
from gundy_ai.data_pipelines import (
    # Core components
    DocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
    # Configuration (most important!)
    configure_for_openai,
    configure_for_claude,
    configure_for_local_llm,
    # Data types
    ChunkingStrategy,
    # Utilities
    ChunkSplittingFilter,
    # Convenience function
    quick_setup,
)


async def create_sample_document():
    """Create a sample document for demonstration."""
    content = """
# Quick Start Guide

Welcome to the data_pipelines library! This guide will get you up and running quickly.

## What This Library Does

The data_pipelines library provides everything you need to process documents for AI applications:

- **Document Processing**: Extract text from PDFs, Word docs, HTML, and more
- **Smart Chunking**: Break text into optimal chunks for your AI model
- **LLM Optimization**: Pre-configured settings for OpenAI, Claude, and local models
- **Advanced Features**: OCR, text cleaning, semantic chunking, and more

## Basic Usage

The simplest way to get started is with the quick_setup function:

```python
from gundy_ai.data_pipelines import quick_setup

# One line setup for OpenAI GPT-4
processor = quick_setup("openai", "gpt-4")
result = await processor.process("document.pdf")
```

## Configuration

Configure the library for your specific LLM:

```python
from gundy_ai.data_pipelines import configure_for_openai, DocumentProcessor

# Configure once, use everywhere
configure_for_openai("gpt-4")

# All components now use optimal settings for GPT-4
processor = DocumentProcessor(ProcessorConfig(name="my_processor"))
```

## Advanced Features

When you need more control, the library provides advanced features:

- Multiple PDF parsers with automatic fallback
- OCR for scanned documents  
- Semantic chunking for better retrieval
- Text cleaning and normalization
- Audit logging and metrics
- Plugin system for extensibility

## Best Practices

1. **Configure Early**: Set up your LLM configuration at the start of your application
2. **Use Semantic Chunking**: For RAG applications, semantic chunking improves retrieval quality
3. **Enable OCR**: For documents that might be scanned or have poor text extraction
4. **Monitor Chunk Sizes**: Ensure chunks fit within your model's context window
5. **Test Different Strategies**: Different document types benefit from different approaches

## Getting Help

- Check the examples directory for more detailed demonstrations
- Use the configuration presets for common LLM providers
- Enable audit logging to understand processing behavior
- Refer to the documentation for advanced features

Happy processing!
    """.strip()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        return f.name


async def demonstrate_quick_setup():
    """Demonstrate the quick_setup convenience function."""
    print("🚀 Quick Setup Demo")
    print("=" * 30)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # One-line setup for different providers
        providers = [
            ("openai", "gpt-4"),
            ("claude", ""),
            ("local", "4096"),
        ]

        for provider, model in providers:
            print(f"\n📋 {provider.title()} Setup:")

            # Quick setup
            processor = quick_setup(provider, model)

            # Process document
            result = await processor.process(doc_path)

            if result.success:
                document = result.data
                print(
                    f"   ✅ Success: {len(document.full_text):,} characters extracted"
                )
                print(f"   📄 Word count: {document.metadata.word_count}")

                # Show configuration that was applied
                from gundy_ai.data_pipelines import get_config

                config = get_config().chunking
                print(f"   ⚙️ Max tokens: {config.max_tokens:,}")
                print(f"   🎯 Target tokens: {config.target_tokens:,}")
            else:
                print(f"   ❌ Failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_manual_configuration():
    """Demonstrate manual configuration for more control."""
    print("⚙️ Manual Configuration Demo")
    print("=" * 35)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Configure for OpenAI GPT-4
        configure_for_openai("gpt-4")
        print("📋 Configured for OpenAI GPT-4")

        # Create processor with specific features
        processor = DocumentProcessor(
            config=ProcessorConfig(name="manual_processor"),
            # Enable advanced features
            pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf"],
            enable_ocr_fallback=True,
            enable_text_cleaning=True,
            text_cleaning_strategy="auto",
        )

        # Process document
        result = await processor.process(doc_path)

        if result.success:
            document = result.data
            metadata = result.metadata

            print(f"✅ Processing successful")
            print(f"   📊 Text length: {len(document.full_text):,} characters")
            print(f"   🔧 Parser used: {metadata.get('parser_used', 'basic')}")
            print(
                f"   🧹 Text cleaning: {'enabled' if 'enable_text_cleaning' else 'disabled'}"
            )

            # Show sample text
            preview = (
                document.full_text[:150] + "..."
                if len(document.full_text) > 150
                else document.full_text
            )
            print(f"   📝 Preview: {repr(preview)}")
        else:
            print(f"❌ Processing failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_chunking_workflow():
    """Demonstrate complete document processing and chunking workflow."""
    print("🔗 Complete Workflow Demo")
    print("=" * 30)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Step 1: Configure for your LLM
        configure_for_openai("gpt-4")
        print("Step 1: ✅ Configured for OpenAI GPT-4")

        # Step 2: Process document
        processor = DocumentProcessor(
            config=ProcessorConfig(name="workflow_processor"), enable_text_cleaning=True
        )

        doc_result = await processor.process(doc_path)
        print(
            f"Step 2: ✅ Document processed ({len(doc_result.data.full_text):,} chars)"
        )

        # Step 3: Chunk the text
        chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="workflow_chunker"),
            strategy=ChunkingStrategy.SEMANTIC,  # Best for RAG
        )

        chunk_result = await chunker.process(doc_result.data)
        print(f"Step 3: ✅ Text chunked ({len(chunk_result.data.chunks)} chunks)")

        # Step 4: Check for oversized chunks and split if needed
        chunked_doc = chunk_result.data

        # Check chunk sizes (rough token estimate)
        from gundy_ai.data_pipelines import get_config

        max_tokens = get_config().chunking.max_tokens

        oversized = []
        for i, chunk in enumerate(chunked_doc.chunks):
            estimated_tokens = len(chunk.content) // 4
            if estimated_tokens > max_tokens:
                oversized.append((i, estimated_tokens))

        if oversized:
            print(f"Step 4: ⚠️ Found {len(oversized)} oversized chunks, splitting...")

            # Split oversized chunks
            splitter = ChunkSplittingFilter()
            final_doc = await splitter.filter_document(chunked_doc)

            print(f"Step 4: ✅ Chunks split ({len(final_doc.chunks)} final chunks)")
            chunked_doc = final_doc
        else:
            print(f"Step 4: ✅ All chunks within size limits")

        # Step 5: Show results
        print(f"\n📊 Final Results:")
        print(f"   📄 Original document: {len(doc_result.data.full_text):,} characters")
        print(f"   🧩 Final chunks: {len(chunked_doc.chunks)}")

        if chunked_doc.chunks:
            chunk_sizes = [
                len(chunk.content) // 4 for chunk in chunked_doc.chunks
            ]  # Token estimate
            avg_tokens = sum(chunk_sizes) / len(chunk_sizes)
            max_chunk_tokens = max(chunk_sizes)

            print(f"   📊 Average chunk size: ~{avg_tokens:.0f} tokens")
            print(f"   📏 Largest chunk: ~{max_chunk_tokens} tokens")
            print(
                f"   ✅ All within {max_tokens} token limit: {'Yes' if max_chunk_tokens <= max_tokens else 'No'}"
            )

            # Show first chunk
            first_chunk = chunked_doc.chunks[0]
            preview = (
                first_chunk.content[:100] + "..."
                if len(first_chunk.content) > 100
                else first_chunk.content
            )
            print(f"   📝 First chunk: {repr(preview)}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_provider_switching():
    """Demonstrate switching between different LLM providers."""
    print("🔄 Provider Switching Demo")
    print("=" * 32)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Process same document with different provider configurations
        providers = [
            ("OpenAI GPT-4", lambda: configure_for_openai("gpt-4")),
            ("Claude", lambda: configure_for_claude()),
            ("Local 8K Model", lambda: configure_for_local_llm(8192)),
        ]

        processor = DocumentProcessor(
            config=ProcessorConfig(name="switching_processor")
        )

        doc_result = await processor.process(doc_path)
        document = doc_result.data

        for provider_name, config_func in providers:
            print(f"\n📋 {provider_name}:")

            # Switch configuration
            config_func()

            # Create chunker (will use new configuration)
            chunker = EnhancedTextChunker(
                config=ProcessorConfig(
                    name=f"chunker_{provider_name.lower().replace(' ', '_')}"
                ),
                strategy=ChunkingStrategy.TOKEN_AWARE,
            )

            # Chunk with new configuration
            chunk_result = await chunker.process(document)

            if chunk_result.success:
                chunked_doc = chunk_result.data

                # Show configuration and results
                from gundy_ai.data_pipelines import get_config

                config = get_config().chunking

                chunk_token_counts = [
                    len(chunk.content) // 4 for chunk in chunked_doc.chunks
                ]
                avg_tokens = (
                    sum(chunk_token_counts) / len(chunk_token_counts)
                    if chunk_token_counts
                    else 0
                )

                print(f"   ⚙️ Max tokens: {config.max_tokens:,}")
                print(f"   🧩 Chunks created: {len(chunked_doc.chunks)}")
                print(f"   📊 Average chunk size: ~{avg_tokens:.0f} tokens")
            else:
                print(f"   ❌ Chunking failed: {chunk_result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def main():
    """Main demo function."""
    print("🚀 Data Pipelines - Quick Start Guide")
    print("=" * 50)
    print()
    print("This guide demonstrates the simplified API for common use cases.")
    print("The library now provides a clean, focused interface while keeping")
    print("all advanced features available when needed.")
    print()

    await demonstrate_quick_setup()
    await demonstrate_manual_configuration()
    await demonstrate_chunking_workflow()
    await demonstrate_provider_switching()

    print("🎯 Key Benefits of the Simplified API:")
    print("   ✅ Fewer imports needed for common use cases")
    print("   ✅ Quick setup function for instant configuration")
    print("   ✅ Automatic LLM optimization with simple configuration")
    print("   ✅ Advanced features still available when needed")
    print("   ✅ Clear separation between basic and advanced usage")
    print()

    print("💡 Next Steps:")
    print("   • Try the quick_setup() function for rapid prototyping")
    print("   • Use configure_for_* functions for production setup")
    print("   • Explore advanced_pdf_demo.py for PDF-specific features")
    print("   • Check advanced_chunking_demo.py for chunking strategies")
    print("   • Import from submodules for specialized components")
    print()

    print("📚 Advanced Features Available:")
    print("   • gundy_ai.data_pipelines.parsers - PDF parsers and OCR")
    print("   • gundy_ai.data_pipelines.text_cleaning - Text cleaning")
    print("   • gundy_ai.data_pipelines.output_formats - Output writers")
    print("   • gundy_ai.data_pipelines.plugins - Plugin system")
    print("   • gundy_ai.data_pipelines.metrics - Observability")


if __name__ == "__main__":
    asyncio.run(main())
