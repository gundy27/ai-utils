"""Basic usage example for gundy-ai-extractors."""

from pathlib import Path
import tempfile

from gundy_ai.extractors import ParserRegistry, TXTParser


def main():
    """Demonstrate basic usage of extractors library."""

    # Create registry and register TXT parser
    registry = ParserRegistry()
    registry.register(TXTParser())

    # List available parsers
    print("Available Parsers:")
    for manifest in registry.list_parsers():
        print(f"  - {manifest.name} v{manifest.version}")
        print(f"    Supports: {', '.join(manifest.supported_types)}")

    print(f"\nSupported extensions: {', '.join(registry.get_supported_extensions())}")

    # Create a sample text file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a sample document.\n")
        f.write("It demonstrates the extraction library.\n")
        f.write("\n")
        f.write(
            "The TXT parser reads the entire file and returns it as a single chunk."
        )
        temp_path = f.name

    try:
        # Get parser for .txt extension
        parser = registry.get_parser(".txt")
        if parser is None:
            print("No parser found for .txt files")
            return

        print(f"\nUsing parser: {parser}")

        # Parse the file
        chunks = parser.parse(temp_path)

        print("\nExtraction Results:")
        print(f"  Chunks: {len(chunks)}")

        for i, chunk in enumerate(chunks):
            print(f"\n  Chunk {i + 1}:")
            print(f"    Text length: {len(chunk.text)} characters")
            print(f"    Span: {chunk.span_start}-{chunk.span_end}")
            print(f"    Metadata: {chunk.metadata}")
            print(f"    Preview: {chunk.text[:100]}...")

        # Health check
        print("\nHealth Check:")
        health_results = registry.health_check_all()
        for parser_name, is_healthy in health_results.items():
            status = "✓ Healthy" if is_healthy else "✗ Unhealthy"
            print(f"  {parser_name}: {status}")

    finally:
        # Cleanup
        Path(temp_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
