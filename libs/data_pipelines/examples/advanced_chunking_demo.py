"""Comprehensive chunking demo showing semantic chunking, token-aware chunking, and chunk splitting."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.data_pipelines import (
    DocumentProcessor,
    ProcessorConfig,
    EnhancedTextChunker,
    ChunkingStrategy,
    ChunkSplittingFilter,
    configure_for_openai,
    configure_for_claude,
    configure_for_local_llm,
    get_config,
)


async def create_sample_document():
    """Create a sample document for chunking demonstrations."""
    content = """
# Advanced Chunking Strategies in AI Systems

## Introduction

Text chunking is a critical component in modern AI systems, particularly for Retrieval Augmented Generation (RAG) applications. The choice of chunking strategy can significantly impact the quality of information retrieval and the effectiveness of language model responses.

## Semantic Chunking

Semantic chunking groups text based on meaning rather than arbitrary size limits. This approach uses embedding models to understand the semantic similarity between sentences and paragraphs, creating chunks that maintain topical coherence.

### Benefits of Semantic Chunking

1. **Topical Coherence**: Chunks maintain semantic unity, improving retrieval relevance
2. **Context Preservation**: Related information stays together, providing better context for language models
3. **Adaptive Sizing**: Chunk sizes vary based on content density and topic boundaries
4. **Improved Retrieval**: More relevant chunks lead to better retrieval results in RAG systems

### Implementation Considerations

When implementing semantic chunking, consider the embedding model choice, similarity thresholds, and computational overhead. The quality of embeddings directly impacts chunking effectiveness.

## Token-Aware Chunking

Token-aware chunking ensures chunks fit within language model context windows while preserving sentence and paragraph boundaries when possible.

### Key Features

- **Token Counting**: Uses actual tokenizer to count tokens accurately
- **Boundary Preservation**: Respects sentence and paragraph boundaries
- **Overlap Management**: Configurable overlap between chunks for context continuity
- **Model Compatibility**: Supports different tokenizers (GPT-4, Claude, etc.)

### Configuration Options

Token-aware chunking can be configured for different models:
- OpenAI models: 8,192 token limit with cl100k_base encoding
- Claude: 100,000+ token limit with larger chunks
- Local models: Variable limits based on model architecture

## Structure-Aware Chunking

Structure-aware chunking respects document hierarchy, keeping headings with their content and maintaining logical document structure.

### Document Structure Elements

- **Headings**: Section titles and subsections
- **Paragraphs**: Logical text blocks
- **Lists**: Enumerated and bulleted items
- **Tables**: Structured data (when applicable)
- **Code Blocks**: Programming code or technical content

## Chunk Splitting and Post-Processing

Sometimes initial chunking produces chunks that are too large for specific use cases. Chunk splitting provides a solution by intelligently dividing oversized chunks while maintaining readability.

### Splitting Strategies

1. **Sentence Splitting**: Divide at sentence boundaries
2. **Paragraph Splitting**: Split at paragraph breaks
3. **Character Splitting**: Last resort for very long sentences

### Quality Preservation

The splitting process prioritizes maintaining semantic coherence and readability over strict size limits.

## Performance Considerations

Different chunking strategies have varying computational requirements:

- **Fixed Size**: Fastest, minimal processing
- **Sentence Boundary**: Fast, good balance
- **Semantic**: Slower, requires embedding computation
- **Structure-Aware**: Medium speed, depends on document complexity

## Best Practices

1. **Choose Strategy Based on Use Case**: Academic papers benefit from structure-aware chunking, while simple documents work well with sentence boundary chunking
2. **Consider Model Limits**: Ensure chunks fit within your target model's context window
3. **Test and Iterate**: Different document types may require different strategies
4. **Monitor Performance**: Track chunking quality and retrieval effectiveness
5. **Use Overlap Wisely**: Overlap improves context but increases storage and processing costs

## Conclusion

Effective chunking is essential for successful AI applications. The choice of strategy should align with your specific use case, document types, and performance requirements. Modern chunking systems provide flexibility to adapt to different scenarios while maintaining high-quality results.
    """.strip()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        return f.name


async def demonstrate_semantic_chunking():
    """Demonstrate semantic chunking capabilities."""
    print("🧠 Semantic Chunking Demo")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Process document
        processor = DocumentProcessor(config=ProcessorConfig(name="doc_processor"))

        doc_result = await processor.process(doc_path)
        document = doc_result.data

        # Create semantic chunker
        chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="semantic_chunker"),
            strategy=ChunkingStrategy.SEMANTIC,
            chunk_size=1000,  # Target size
        )

        result = await chunker.process(document)

        if result.success:
            chunked_doc = result.data

            print(f"✅ Semantic chunking successful")
            print(f"   📄 Original text: {len(document.full_text):,} characters")
            print(f"   🧩 Chunks created: {len(chunked_doc.chunks)}")

            # Analyze chunk characteristics
            chunk_sizes = [len(chunk.content) for chunk in chunked_doc.chunks]
            avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0

            print(f"   📊 Average chunk size: {avg_size:.0f} characters")
            print(
                f"   📏 Size range: {min(chunk_sizes)} - {max(chunk_sizes)} characters"
            )

            # Show first few chunks
            print(f"   📝 Sample chunks:")
            for i, chunk in enumerate(chunked_doc.chunks[:3]):
                preview = (
                    chunk.content[:100] + "..."
                    if len(chunk.content) > 100
                    else chunk.content
                )
                print(f"      Chunk {i+1}: {repr(preview)}")
        else:
            print(f"❌ Semantic chunking failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_token_aware_chunking():
    """Demonstrate token-aware chunking with different model configurations."""
    print("🎯 Token-Aware Chunking Demo")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Process document
        processor = DocumentProcessor(config=ProcessorConfig(name="doc_processor"))

        doc_result = await processor.process(doc_path)
        document = doc_result.data

        # Test different model configurations
        configurations = [
            ("OpenAI GPT-4", lambda: configure_for_openai("gpt-4")),
            ("Claude", lambda: configure_for_claude()),
            ("Local 4K Model", lambda: configure_for_local_llm(4096)),
        ]

        for config_name, config_func in configurations:
            print(f"\n📋 {config_name} Configuration:")

            # Apply configuration
            config_func()
            current_config = get_config().chunking

            print(f"   Max tokens: {current_config.max_tokens:,}")
            print(f"   Target tokens: {current_config.target_tokens:,}")
            print(f"   Overlap: {current_config.overlap_tokens}")

            # Create token-aware chunker
            chunker = EnhancedTextChunker(
                config=ProcessorConfig(
                    name=f"token_chunker_{config_name.lower().replace(' ', '_')}"
                ),
                strategy=ChunkingStrategy.TOKEN_AWARE,
            )

            result = await chunker.process(document)

            if result.success:
                chunked_doc = result.data

                # Estimate token counts (rough approximation)
                chunk_token_counts = [
                    len(chunk.content) // 4 for chunk in chunked_doc.chunks
                ]
                avg_tokens = (
                    sum(chunk_token_counts) / len(chunk_token_counts)
                    if chunk_token_counts
                    else 0
                )
                max_tokens = max(chunk_token_counts) if chunk_token_counts else 0

                print(f"   ✅ Chunking successful")
                print(f"      🧩 Chunks: {len(chunked_doc.chunks)}")
                print(f"      📊 Avg tokens: ~{avg_tokens:.0f}")
                print(f"      📏 Max tokens: ~{max_tokens}")
                print(
                    f"      ✅ Within limits: {'Yes' if max_tokens <= current_config.max_tokens else 'No'}"
                )
            else:
                print(f"   ❌ Chunking failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_structure_aware_chunking():
    """Demonstrate structure-aware chunking."""
    print("🏗️ Structure-Aware Chunking Demo")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Process document
        processor = DocumentProcessor(config=ProcessorConfig(name="doc_processor"))

        doc_result = await processor.process(doc_path)
        document = doc_result.data

        # Create structure-aware chunker
        chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="structure_chunker"),
            strategy=ChunkingStrategy.STRUCTURE_AWARE,
            chunk_size=800,
        )

        result = await chunker.process(document)

        if result.success:
            chunked_doc = result.data

            print(f"✅ Structure-aware chunking successful")
            print(f"   📄 Original text: {len(document.full_text):,} characters")
            print(f"   🧩 Chunks created: {len(chunked_doc.chunks)}")

            # Show how structure is preserved
            print(f"   📝 Structure preservation examples:")
            for i, chunk in enumerate(chunked_doc.chunks[:3]):
                # Look for headings in chunks
                lines = chunk.content.split("\n")
                headings = [line for line in lines if line.strip().startswith("#")]

                if headings:
                    print(
                        f"      Chunk {i+1}: Contains heading '{headings[0].strip()}'"
                    )
                else:
                    preview = (
                        chunk.content[:80] + "..."
                        if len(chunk.content) > 80
                        else chunk.content
                    )
                    print(f"      Chunk {i+1}: {repr(preview)}")
        else:
            print(f"❌ Structure-aware chunking failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_chunk_splitting():
    """Demonstrate chunk splitting for oversized chunks."""
    print("✂️ Chunk Splitting Demo")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Configure for small context window to force oversized chunks
        configure_for_local_llm(2048)

        # Process document
        processor = DocumentProcessor(config=ProcessorConfig(name="doc_processor"))

        doc_result = await processor.process(doc_path)
        document = doc_result.data

        # Create chunker that might produce oversized chunks
        chunker = EnhancedTextChunker(
            config=ProcessorConfig(name="large_chunker"),
            strategy=ChunkingStrategy.STRUCTURE_AWARE,
            chunk_size=8000,  # Intentionally large
        )

        chunk_result = await chunker.process(document)

        if chunk_result.success:
            regular_doc = chunk_result.data

            # Check for oversized chunks
            max_tokens = get_config().chunking.max_tokens
            oversized = []

            for i, chunk in enumerate(regular_doc.chunks):
                estimated_tokens = len(chunk.content) // 4
                if estimated_tokens > max_tokens:
                    oversized.append((i, estimated_tokens))

            print(f"📊 Initial chunking results:")
            print(f"   🧩 Chunks created: {len(regular_doc.chunks)}")
            print(f"   ⚠️ Oversized chunks: {len(oversized)}")
            print(f"   📏 Token limit: {max_tokens}")

            if oversized:
                print(f"   📋 Oversized chunk details:")
                for chunk_idx, token_count in oversized:
                    print(
                        f"      Chunk {chunk_idx}: ~{token_count} tokens (exceeds {max_tokens})"
                    )

                # Apply chunk splitting filter
                chunk_filter = ChunkSplittingFilter()
                filtered_doc = await chunk_filter.filter_document(regular_doc)

                print("✅ Chunk splitting applied")
                print(f"   Original chunks: {len(regular_doc.chunks)}")
                print(f"   Final chunks: {len(filtered_doc.chunks)}")

                # Verify all chunks are within limits
                final_oversized = []
                split_chunks = 0

                for i, chunk in enumerate(filtered_doc.chunks):
                    estimated_tokens = len(chunk.content) // 4
                    if estimated_tokens > max_tokens:
                        final_oversized.append((i, estimated_tokens))

                    # Check if this chunk was split (has split metadata)
                    if hasattr(chunk, "metadata") and chunk.metadata:
                        split_info = chunk.metadata.get("split_info")
                        if split_info:
                            split_chunks += 1
                            print(
                                f"      Split chunk {i}: Part {split_info['split_part']}/{split_info['split_total']}"
                            )

                print("📊 Final statistics:")
                print(f"   Total chunks: {len(filtered_doc.chunks)}")
                print(f"   Split chunks: {split_chunks}")
                print(f"   Remaining oversized: {len(final_oversized)}")
                print(
                    f"   ✅ All within limits: {'Yes' if not final_oversized else 'No'}"
                )
            else:
                print("   ✅ No oversized chunks found")
        else:
            print(f"❌ Initial chunking failed: {chunk_result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_chunking_comparison():
    """Compare different chunking strategies side by side."""
    print("⚖️ Chunking Strategy Comparison")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_document()

    try:
        # Process document once
        processor = DocumentProcessor(config=ProcessorConfig(name="doc_processor"))

        doc_result = await processor.process(doc_path)
        document = doc_result.data

        # Test different strategies
        strategies = [
            (ChunkingStrategy.SENTENCE_BOUNDARY, "Sentence Boundary"),
            (ChunkingStrategy.SEMANTIC, "Semantic"),
            (ChunkingStrategy.STRUCTURE_AWARE, "Structure-Aware"),
            (ChunkingStrategy.TOKEN_AWARE, "Token-Aware"),
        ]

        print(f"📄 Document: {len(document.full_text):,} characters")
        print(f"📊 Strategy comparison:")
        print()

        results = []

        for strategy, name in strategies:
            chunker = EnhancedTextChunker(
                config=ProcessorConfig(name=f"chunker_{strategy.value}"),
                strategy=strategy,
                chunk_size=1000,
            )

            result = await chunker.process(document)

            if result.success:
                chunked_doc = result.data
                chunk_sizes = [len(chunk.content) for chunk in chunked_doc.chunks]
                avg_size = sum(chunk_sizes) / len(chunk_sizes) if chunk_sizes else 0

                results.append(
                    {
                        "name": name,
                        "chunks": len(chunked_doc.chunks),
                        "avg_size": avg_size,
                        "min_size": min(chunk_sizes) if chunk_sizes else 0,
                        "max_size": max(chunk_sizes) if chunk_sizes else 0,
                    }
                )
            else:
                results.append({"name": name, "error": result.error})

        # Display results in table format
        print(
            f"{'Strategy':<20} {'Chunks':<8} {'Avg Size':<10} {'Min Size':<10} {'Max Size':<10}"
        )
        print("-" * 70)

        for result in results:
            if "error" in result:
                print(f"{result['name']:<20} {'ERROR':<8} {result['error']}")
            else:
                print(
                    f"{result['name']:<20} {result['chunks']:<8} {result['avg_size']:<10.0f} {result['min_size']:<10} {result['max_size']:<10}"
                )

        print()
        print("💡 Strategy Selection Guide:")
        print("   • Sentence Boundary: Fast, good for simple documents")
        print("   • Semantic: Best for topical coherence, slower")
        print("   • Structure-Aware: Preserves document hierarchy")
        print("   • Token-Aware: Optimized for LLM context windows")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def main():
    """Main demo function."""
    print("🚀 Advanced Chunking Strategies Demo")
    print("=" * 60)
    print()
    print("This demo showcases the advanced chunking capabilities")
    print("of the data_pipelines library, including:")
    print("• Semantic chunking based on content similarity")
    print("• Token-aware chunking for LLM optimization")
    print("• Structure-aware chunking for document hierarchy")
    print("• Automatic chunk splitting for oversized content")
    print("• Strategy comparison and selection guidance")
    print()

    await demonstrate_semantic_chunking()
    await demonstrate_token_aware_chunking()
    await demonstrate_structure_aware_chunking()
    await demonstrate_chunk_splitting()
    await demonstrate_chunking_comparison()

    print("🎯 Key Takeaways:")
    print("   ✅ Different strategies optimize for different use cases")
    print("   ✅ Token-aware chunking ensures LLM compatibility")
    print("   ✅ Semantic chunking improves retrieval relevance")
    print("   ✅ Structure-aware chunking preserves document context")
    print("   ✅ Chunk splitting handles oversized content gracefully")
    print("   ✅ Configuration system makes strategy switching easy")
    print()

    print("💡 Best Practices:")
    print("   • Choose strategy based on document type and use case")
    print("   • Use token-aware chunking for LLM applications")
    print("   • Consider semantic chunking for RAG systems")
    print("   • Test different strategies with your specific content")
    print("   • Monitor chunk sizes and adjust configurations as needed")


if __name__ == "__main__":
    asyncio.run(main())
