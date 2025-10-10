"""Example client for RAG API."""

import sys

import httpx


class RAGClient:
    """Simple client for RAG API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client.

        Args:
            base_url: Base URL of API
        """
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=60.0)

    def health_check(self) -> dict:
        """Check API health."""
        response = self.client.get("/health")
        response.raise_for_status()
        return response.json()

    def get_stats(self) -> dict:
        """Get API statistics."""
        response = self.client.get("/stats")
        response.raise_for_status()
        return response.json()

    def ingest_document(self, file_path: str, metadata: dict = None) -> dict:
        """Ingest a document.

        Args:
            file_path: Path to document file
            metadata: Optional metadata dictionary

        Returns:
            Ingestion result
        """
        with open(file_path, "rb") as f:
            files = {"file": (file_path, f, "application/octet-stream")}
            data = {"metadata": str(metadata or {})}

            response = self.client.post("/documents/ingest", files=files, data=data)
            response.raise_for_status()
            return response.json()

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter: dict = None,
        include_text: bool = True,
    ) -> dict:
        """Search documents.

        Args:
            query: Search query
            top_k: Number of results
            filter: Optional metadata filter
            include_text: Include text in results

        Returns:
            Search results
        """
        payload = {
            "query": query,
            "top_k": top_k,
            "include_text": include_text,
        }
        if filter:
            payload["filter"] = filter

        response = self.client.post("/search", json=payload)
        response.raise_for_status()
        return response.json()


def main():
    """Run example workflow."""
    print("=== RAG API Client Example ===\n")

    client = RAGClient()

    # 1. Check health
    print("1. Checking API health...")
    health = client.health_check()
    print(f"   Status: {health['status']}")
    for name, component in health["components"].items():
        status = "✓" if component["healthy"] else "✗"
        print(f"   {status} {name}: {component.get('message', 'OK')}")

    print()

    # 2. Get stats
    print("2. Getting API stats...")
    stats = client.get_stats()
    print(f"   Vectors: {stats['vector_count']}")
    print(f"   Model: {stats['embedding_model']}")
    print(f"   Supported types: {', '.join(stats['supported_file_types'])}")

    print()

    # 3. Ingest document (if file provided)
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        print(f"3. Ingesting document: {file_path}")
        result = client.ingest_document(file_path, metadata={"source": "cli"})
        print(f"   Document ID: {result['document_id']}")
        print(f"   Chunks: {result['chunks_created']}")
        print(f"   Tokens: {result['total_tokens']}")
        print(f"   Cost: ${result['estimated_cost_usd']:.6f}")
        print(f"   Time: {result['processing_time_ms']:.1f}ms")

        print()

    # 4. Search
    query = sys.argv[2] if len(sys.argv) > 2 else "What is this document about?"
    print(f'4. Searching: "{query}"')
    results = client.search(query, top_k=3)
    print(
        f"   Found {results['total_results']} results in {results['processing_time_ms']:.1f}ms"
    )

    for i, result in enumerate(results["results"]):
        print(f"\n   Result {i + 1}:")
        print(f"     Score: {result['score']:.3f}")
        print(f"     Document: {result['document_id']}")
        if result.get("text"):
            text_preview = (
                result["text"][:100] + "..."
                if len(result["text"]) > 100
                else result["text"]
            )
            print(f'     Text: "{text_preview}"')

    print("\n✓ Complete!")


if __name__ == "__main__":
    try:
        main()
    except httpx.HTTPError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n✗ File not found: {e}")
        sys.exit(1)
