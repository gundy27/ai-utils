"""Example demonstrating centralized configuration for chunk sizes."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.data_pipelines import (
    # Core components
    EnhancedDocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
    ChunkSplittingFilter,
    # Configuration
    ChunkingConfig,
    ProcessingConfig,
    configure_for_openai,
    configure_for_claude,
    configure_for_local_llm,
    get_config,
    set_config,
)


async def create_sample_document():
    """Create a sample document for testing."""
    content = """
# Centralized Configuration Demo

This document demonstrates how the centralized configuration system works
in the data_pipelines library. The configuration system allows you to:

1. Set chunk sizes globally for all components
2. Configure for specific LLM providers (OpenAI, Claude, local models)
3. Use environment variables for configuration
4. Override settings per component when needed

## Benefits of Centralized Configuration

### Consistency
All components use the same chunk size settings by default, ensuring
consistency across your entire processing pipeline.

### Flexibility
You can still override settings for specific components when needed,
while maintaining global defaults for everything else.

### LLM Optimization
Pre-configured settings for popular LLM providers ensure optimal
chunk sizes for different models and their token limits.

### Environment-Based Configuration
Support for environment variables makes it easy to configure
different settings for development, staging, and production environments.

## Configuration Hierarchy

The configuration system follows this hierarchy (highest to lowest priority):

1. Explicit parameters passed to components
2. Custom ChunkingConfig passed to components
3. Global configuration set via set_config()
4. Environment variables
5. Default values

This allows maximum flexibility while providing sensible defaults.
    """.strip()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        return f.name


async def demonstrate_configuration_options():
    """Demonstrate different configuration options."""

    print("⚙️  Centralized Configuration Demo")
    print("=" * 50)
    print()

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Initialize document processor
        processor = EnhancedDocumentProcessor(
            config=ProcessorConfig(name="config_demo")
        )

        # Process document once
        doc_result = await processor.process(doc_path)
        if not doc_result.success:
            print(f"❌ Document processing failed: {doc_result.error}")
            return

        document = doc_result.data
        print(f"📄 Document processed: {len(document.full_text):,} characters")
        print()

        # Test different configuration approaches
        configurations = [
            {
                "name": "Default Configuration",
                "setup": lambda: None,  # Use defaults
                "description": "Uses built-in defaults",
            },
            {
                "name": "OpenAI GPT-4 Configuration",
                "setup": lambda: configure_for_openai("gpt-4"),
                "description": "Optimized for OpenAI GPT-4 (8,192 token limit)",
            },
            {
                "name": "OpenAI GPT-3.5 Configuration",
                "setup": lambda: configure_for_openai("gpt-3.5-turbo"),
                "description": "Optimized for OpenAI GPT-3.5-turbo (8,192 token limit)",
            },
            {
                "name": "Claude Configuration",
                "setup": lambda: configure_for_claude(),
                "description": "Optimized for Claude (100,000+ token limit)",
            },
            {
                "name": "Local 4K Model Configuration",
                "setup": lambda: configure_for_local_llm(4096),
                "description": "Optimized for local models with 4K context",
            },
            {
                "name": "Local 16K Model Configuration",
                "setup": lambda: configure_for_local_llm(16384),
                "description": "Optimized for local models with 16K context",
            },
            {
                "name": "Custom Configuration",
                "setup": lambda: set_config(
                    ProcessingConfig(
                        chunking=ChunkingConfig(
                            max_tokens=6000,
                            target_tokens=3000,
                            overlap_tokens=300,
                            encoding_name="cl100k_base",
                        )
                    )
                ),
                "description": "Custom settings for specific use case",
            },
        ]

        for config_info in configurations:
            print(f"🔧 Testing: {config_info['name']}")
            print(f"   {config_info['description']}")

            # Apply configuration
            config_info["setup"]()

            # Get current configuration
            current_config = get_config()
            chunking_config = current_config.chunking

            print("   Settings:")
            print(f"     Max tokens: {chunking_config.max_tokens:,}")
            print(f"     Target tokens: {chunking_config.target_tokens:,}")
            print(f"     Overlap tokens: {chunking_config.overlap_tokens}")
            print(f"     Encoding: {chunking_config.encoding_name}")

            # Test chunking with this configuration
            chunker = EnhancedTextChunker(
                config=ProcessorConfig(
                    name=f"chunker_{config_info['name'].lower().replace(' ', '_')}"
                ),
                strategy="token_aware",
                # Note: No chunk_size specified - uses global config!
            )

            chunk_result = await chunker.process(document)

            if chunk_result.success:
                chunked_doc = chunk_result.data

                # Analyze results
                chunk_sizes = [
                    len(chunk.content) // 4 for chunk in chunked_doc.chunks
                ]  # Rough token estimate
                avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0
                max_size = max(chunk_sizes) if chunk_sizes else 0

                print("   Results:")
                print(f"     Chunks created: {len(chunked_doc.chunks)}")
                print(f"     Average size: ~{avg_size:.0f} tokens")
                print(f"     Max size: ~{max_size:.0f} tokens")
                print(
                    f"     Within limits: {'✅' if max_size <= chunking_config.max_tokens else '❌'}"
                )
            else:
                print(f"   ❌ Chunking failed: {chunk_result.error}")

            print()

        # Demonstrate component-level overrides
        print("🎯 Component-Level Overrides Demo")
        print("=" * 40)
        print()

        # Set global configuration
        configure_for_openai("gpt-4")
        global_config = get_config().chunking
        print(f"Global config: {global_config.target_tokens} target tokens")

        # Create chunker that uses global config
        global_chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="global_chunker"),
            strategy="token_aware",
            # Uses global config
        )

        # Create chunker with override
        override_chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="override_chunker"),
            strategy="token_aware",
            chunk_size=2000,  # Override global setting
        )

        # Create chunker with custom config
        custom_config = ChunkingConfig(
            max_tokens=6000, target_tokens=3000, overlap_tokens=150
        )

        custom_chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="custom_chunker"),
            strategy="token_aware",
            chunking_config=custom_config,
        )

        # Test all three approaches
        chunkers = [
            ("Global Config", global_chunker, global_config.target_tokens),
            ("Override", override_chunker, 2000),
            ("Custom Config", custom_chunker, custom_config.target_tokens),
        ]

        for name, chunker, expected_size in chunkers:
            result = await chunker.process(document)

            if result.success:
                chunks = result.data.chunks
                avg_size = sum(len(c.content) // 4 for c in chunks) / len(chunks)
                print(
                    f"{name}: {len(chunks)} chunks, ~{avg_size:.0f} avg tokens (expected ~{expected_size})"
                )
            else:
                print(f"{name}: Failed - {result.error}")

        print()

        # Demonstrate ChunkSplittingFilter with global config
        print("✂️  ChunkSplittingFilter with Global Config")
        print("=" * 45)
        print()

        # Create oversized chunks first
        configure_for_local_llm(2048)  # Small context window

        large_chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="large_chunker"),
            strategy="structure_aware",
            chunk_size=8000,  # Intentionally large
        )

        large_result = await large_chunker.process(document)

        if large_result.success:
            large_doc = large_result.data

            # Check for oversized chunks
            oversized = []
            for i, chunk in enumerate(large_doc.chunks):
                estimated_tokens = len(chunk.content) // 4
                if estimated_tokens > get_config().chunking.max_tokens:
                    oversized.append((i, estimated_tokens))

            print(f"Created {len(large_doc.chunks)} chunks")
            print(f"Found {len(oversized)} oversized chunks")

            if oversized:
                # Apply filter (uses global config automatically)
                filter = ChunkSplittingFilter()
                filtered_doc = await filter.filter_document(large_doc)

                print(f"After splitting: {len(filtered_doc.chunks)} chunks")

                # Verify all chunks are within limits
                max_tokens = get_config().chunking.max_tokens
                all_within_limits = all(
                    len(chunk.content) // 4 <= max_tokens
                    for chunk in filtered_doc.chunks
                )
                print(
                    f"All within {max_tokens} token limit: {'✅' if all_within_limits else '❌'}"
                )

        print()

        # Show environment variable configuration
        print("🌍 Environment Variable Configuration")
        print("=" * 40)
        print()

        print("You can configure the library using environment variables:")
        print()
        print("# Token limits")
        print("export CHUNKING_MAX_TOKENS=8192")
        print("export CHUNKING_TARGET_TOKENS=4000")
        print("export CHUNKING_OVERLAP_TOKENS=200")
        print()
        print("# Character limits (fallback)")
        print("export CHUNKING_MAX_CHUNK_SIZE=4000")
        print("export CHUNKING_MIN_CHUNK_SIZE=100")
        print("export CHUNKING_OVERLAP_SIZE=200")
        print()
        print("# Tokenizer")
        print("export CHUNKING_ENCODING=cl100k_base")
        print()
        print("# Structure preservation")
        print("export CHUNKING_PRESERVE_SENTENCES=true")
        print("export CHUNKING_PRESERVE_PARAGRAPHS=true")
        print()
        print("# Processing settings")
        print("export ENABLE_OCR_FALLBACK=true")
        print("export OCR_CONFIDENCE_THRESHOLD=0.6")
        print("export ENABLE_TEXT_CLEANING=true")
        print()

    finally:
        # Cleanup
        Path(doc_path).unlink(missing_ok=True)


async def main():
    """Main demo function."""
    print("🚀 Centralized Configuration System")
    print("=" * 60)
    print()
    print("This demo shows how to easily adjust chunk sizes and other")
    print("settings across the entire data_pipelines library.")
    print()

    await demonstrate_configuration_options()

    print("🎯 Key Benefits:")
    print("   ✅ Single place to configure chunk sizes")
    print("   ✅ Pre-configured settings for popular LLMs")
    print("   ✅ Environment variable support")
    print("   ✅ Component-level overrides when needed")
    print("   ✅ Automatic propagation to all components")
    print("   ✅ Type-safe configuration with validation")
    print()

    print("💡 Quick Usage Examples:")
    print()
    print("# Configure for OpenAI GPT-4")
    print("from gundy_ai.data_pipelines import configure_for_openai")
    print("configure_for_openai('gpt-4')")
    print()
    print("# Configure for Claude")
    print("from gundy_ai.data_pipelines import configure_for_claude")
    print("configure_for_claude()")
    print()
    print("# Configure for local model")
    print("from gundy_ai.data_pipelines import configure_for_local_llm")
    print("configure_for_local_llm(context_window=8192)")
    print()
    print("# Custom configuration")
    print(
        "from gundy_ai.data_pipelines import ChunkingConfig, set_config, ProcessingConfig"
    )
    print("config = ProcessingConfig(")
    print("    chunking=ChunkingConfig(")
    print("        max_tokens=6000,")
    print("        target_tokens=3000,")
    print("        overlap_tokens=300")
    print("    )")
    print(")")
    print("set_config(config)")
    print()
    print("# All components now use these settings automatically!")


if __name__ == "__main__":
    asyncio.run(main())
