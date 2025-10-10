"""Example showing how to create a custom parser."""

import tempfile
from pathlib import Path
from typing import List

from gundy_ai.extractors import BaseParser, ParsedChunk, ParserManifest, ParserRegistry


class JSONParser(BaseParser):
    """Custom parser for JSON files.

    This is a simple example showing how to implement a custom parser.
    """

    @property
    def manifest(self) -> ParserManifest:
        """Define parser capabilities."""
        return ParserManifest(
            name="json",
            version="1.0.0",
            supported_types=[".json"],
            schema_version="1.0",
            dependencies=[],  # Uses built-in json module
        )

    def parse(self, file_path: str) -> List[ParsedChunk]:
        """Parse JSON file and return as text.

        For this simple example, we just read the file and return
        it as formatted JSON text. A more sophisticated version
        could extract specific fields or structure.
        """
        import json

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            # Read and parse JSON
            with open(path, "r") as f:
                data = json.load(f)

            # Convert to pretty-printed text
            text = json.dumps(data, indent=2)

            chunk = ParsedChunk(
                text=text,
                span_start=0,
                span_end=len(text),
                metadata={
                    "parser": "json",
                    "parser_version": "1.0.0",
                    "file_name": path.name,
                    "keys": list(data.keys()) if isinstance(data, dict) else [],
                },
            )

            return [chunk]

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {str(e)}") from e

    def health_check(self) -> bool:
        """JSON parser uses built-in library, always healthy."""
        return True


def main():
    """Demonstrate custom parser usage."""

    print("Custom Parser Example: JSON Parser\n")

    # Create registry and register custom parser
    registry = ParserRegistry()
    registry.register(JSONParser())
    registry.register(
        BaseParser.__subclasses__()[0]()
    )  # Also register a standard parser

    print("Registered Parsers:")
    for manifest in registry.list_parsers():
        print(f"  - {manifest.name} v{manifest.version}")

    # Create sample JSON file
    import json

    sample_data = {
        "name": "Test Document",
        "type": "example",
        "metadata": {"author": "AI Utils", "version": "1.0"},
        "content": ["First item", "Second item", "Third item"],
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_data, f)
        temp_path = f.name

    try:
        # Parse JSON file
        parser = registry.get_parser(".json")
        print(f"\nUsing parser: {parser.manifest.name}")

        chunks = parser.parse(temp_path)

        print("\nExtraction Results:")
        print(f"  Chunks: {len(chunks)}")
        print(f"  Characters: {len(chunks[0].text)}")
        print(f"  Metadata: {chunks[0].metadata}")
        print("\nExtracted Content:")
        print(chunks[0].text)

    finally:
        Path(temp_path).unlink(missing_ok=True)

    print("\n✓ Custom parser working!")
    print("\nTo create your own parser:")
    print("  1. Subclass BaseParser")
    print("  2. Implement manifest property")
    print("  3. Implement parse() method")
    print("  4. Optionally implement health_check()")
    print("  5. Register with ParserRegistry")


if __name__ == "__main__":
    main()
