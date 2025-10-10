"""Basic usage example for gundy-ai-embeddings."""

import os

from gundy_ai.embeddings import OpenAIEmbeddingProvider


def main():
    """Demonstrate basic embedding usage."""

    print("=== Gundy AI Embeddings - Basic Usage ===\n")

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY='your-key-here'")
        return

    # Create provider
    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small")

    print(f"Provider: {provider}")
    print(f"Model: {provider.model_name}")
    print(f"Dimensions: {provider.dimensions}\n")

    # Health check
    print("Running health check...")
    health = provider.health_check()

    if health["healthy"]:
        print(f"✓ Provider healthy (latency: {health['latency_ms']:.1f}ms)\n")
    else:
        print(f"✗ Provider unhealthy: {health.get('error')}\n")
        return

    # Sample texts
    texts = [
        "Machine learning is transforming how we process text.",
        "Embeddings convert text into numerical vectors.",
        "Vector databases enable semantic search.",
    ]

    print(f"Embedding {len(texts)} texts...")
    print()

    # Generate embeddings
    result = provider.embed(texts)

    # Display results
    print("Results:")
    print(f"  Texts embedded: {result.texts_count}")
    print(f"  Embedding dimensions: {result.dimensions}")
    print(f"  Total tokens: {result.total_tokens}")
    print(f"  Latency: {result.latency_ms:.1f}ms")
    print(f"  Estimated cost: ${result.estimated_cost_usd:.6f}")
    print()

    # Show embedding samples
    print("Embedding samples (first 5 dimensions):")
    for i, (text, embedding) in enumerate(zip(texts, result.embeddings)):
        print(f'  {i + 1}. "{text[:40]}..."')
        print(f"     {embedding[:5]}")

    print("\n✓ Embeddings generated successfully!")


if __name__ == "__main__":
    main()
