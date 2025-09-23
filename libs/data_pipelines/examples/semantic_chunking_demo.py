"""Example demonstrating semantic and structure-aware chunking."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.data_pipelines import (
    EnhancedDocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
)


async def main():
    """Demonstrate semantic and structure-aware chunking."""
    print("🧠 Semantic & Structure-Aware Chunking Demo")
    print("=" * 50)

    # Sample text with clear structure and topics
    sample_text = """
# Introduction to Machine Learning

Machine learning is a subset of artificial intelligence that focuses on algorithms that can learn from data. These algorithms build mathematical models based on training data to make predictions or decisions without being explicitly programmed.

## Types of Machine Learning

### Supervised Learning
Supervised learning uses labeled training data to learn a mapping function from inputs to outputs. Common examples include classification and regression tasks. The algorithm learns from input-output pairs and can then make predictions on new, unseen data.

Classification problems involve predicting discrete categories or classes. For example, email spam detection classifies emails as either spam or not spam. Regression problems involve predicting continuous numerical values, such as predicting house prices based on features like size and location.

### Unsupervised Learning
Unsupervised learning works with unlabeled data to discover hidden patterns or structures. The algorithm must find patterns without being told what to look for. Common techniques include clustering and dimensionality reduction.

Clustering algorithms group similar data points together. K-means clustering is a popular algorithm that partitions data into k clusters. Principal Component Analysis (PCA) is a dimensionality reduction technique that finds the most important features in high-dimensional data.

### Reinforcement Learning
Reinforcement learning involves an agent learning to make decisions through interaction with an environment. The agent receives rewards or penalties for its actions and learns to maximize cumulative reward over time.

This approach is particularly useful for sequential decision-making problems. Applications include game playing, robotics, and autonomous vehicle control. The agent must balance exploration of new actions with exploitation of known good actions.

## Applications of Machine Learning

Machine learning has numerous real-world applications across various industries. In healthcare, ML algorithms help with medical diagnosis, drug discovery, and personalized treatment plans. Financial institutions use machine learning for fraud detection, algorithmic trading, and credit scoring.

Technology companies leverage ML for recommendation systems, natural language processing, and computer vision. Social media platforms use machine learning to curate content feeds and detect inappropriate content. Search engines use ML algorithms to rank web pages and understand user queries.

## Conclusion

Machine learning continues to evolve rapidly, with new techniques and applications emerging regularly. As data becomes more abundant and computing power increases, we can expect machine learning to play an even more significant role in solving complex problems across all sectors of society.
    """

    # Create a temporary file with the sample text
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(sample_text)
        temp_file = f.name

    try:
        print("📄 Processing sample document...")

        # Initialize enhanced document processor
        doc_config = ProcessorConfig(name="semantic_demo_doc")
        doc_processor = EnhancedDocumentProcessor(doc_config)

        # Process the document
        doc_result = await doc_processor.process(temp_file)

        if not doc_result.success:
            print(f"❌ Document processing failed: {doc_result.error}")
            return

        document = doc_result.data
        print(f"✅ Document processed: {len(document.full_text)} characters")
        print()

        # Test different chunking strategies
        strategies = [
            ("semantic", "🧠 Semantic Chunking"),
            ("structure_aware", "🏗️  Structure-Aware Chunking"),
            ("fixed_size", "📏 Fixed-Size Chunking (baseline)"),
        ]

        for strategy_name, strategy_title in strategies:
            print(strategy_title)
            print("-" * 40)

            # Initialize chunker
            chunker_config = ProcessorConfig(name=f"chunker_{strategy_name}")

            if strategy_name == "semantic":
                chunker = EnhancedTextChunker(
                    config=chunker_config,
                    strategy="semantic",
                    chunk_size=800,
                    model_name="all-MiniLM-L6-v2",
                    similarity_threshold=0.7,
                    sentence_window=3,
                )
            elif strategy_name == "structure_aware":
                chunker = EnhancedTextChunker(
                    config=chunker_config,
                    strategy="structure_aware",
                    chunk_size=800,
                    preserve_headings=True,
                    preserve_paragraphs=True,
                )
            else:  # fixed_size baseline
                chunker = EnhancedTextChunker(
                    config=chunker_config,
                    strategy="fixed_size",
                    chunk_size=800,
                    overlap=100,
                )

            # Chunk the document
            chunk_result = await chunker.process(document)

            if chunk_result.success:
                chunked_doc = chunk_result.data
                chunks = chunked_doc.chunks

                print(f"✅ Created {len(chunks)} chunks")

                # Show chunk statistics
                token_counts = [chunk.token_count for chunk in chunks]
                avg_tokens = (
                    sum(token_counts) / len(token_counts) if token_counts else 0
                )

                print(f"   📊 Average tokens per chunk: {avg_tokens:.1f}")
                print(f"   📊 Token range: {min(token_counts)} - {max(token_counts)}")

                # Show processing metadata
                metadata = chunk_result.metadata
                if "processing_time_ms" in metadata:
                    print(
                        f"   ⏱️  Processing time: {metadata['processing_time_ms']:.1f}ms"
                    )

                # Show first few chunks with their content
                print("   📝 Sample chunks:")
                for i, chunk in enumerate(chunks[:3]):
                    preview = (
                        chunk.content[:100] + "..."
                        if len(chunk.content) > 100
                        else chunk.content
                    )
                    print(
                        f"      Chunk {i+1} ({chunk.token_count} tokens): {repr(preview)}"
                    )

                    # Show chunk-specific metadata for advanced strategies
                    if (
                        strategy_name == "semantic"
                        and "avg_similarity" in chunk.metadata
                    ):
                        print(
                            f"         Similarity: {chunk.metadata['avg_similarity']:.3f}"
                        )
                    elif (
                        strategy_name == "structure_aware"
                        and "primary_heading" in chunk.metadata
                    ):
                        print(f"         Heading: {chunk.metadata['primary_heading']}")

                print()

            else:
                print(f"❌ Chunking failed: {chunk_result.error}")
                print()

        print("🎯 Key Differences:")
        print("   • Semantic chunking groups related sentences together")
        print("   • Structure-aware chunking preserves document hierarchy")
        print("   • Fixed-size chunking splits at arbitrary boundaries")
        print()
        print("💡 Use Cases:")
        print("   • Semantic: Best for Q&A and retrieval systems")
        print("   • Structure-aware: Best for documents with clear hierarchy")
        print("   • Fixed-size: Fastest, good for simple applications")

    finally:
        # Clean up temporary file
        Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
