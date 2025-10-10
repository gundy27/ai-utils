# Gundy AI Extractors

Document extraction plugins for AI applications with support for multiple file formats.

## Features

- **Plugin Architecture**: Extensible parser system with clean interfaces
- **Multiple Formats**: TXT, MD, CSV (more coming soon)
- **Audit Logging**: Comprehensive event tracking for all extraction operations
- **Type Safety**: Full Pydantic models with validation
- **Test Coverage**: >90% test coverage with comprehensive test suite

## Installation

```bash
poetry add gundy-ai-extractors
```

## Quick Start

```python
from gundy_ai.extractors import ParserRegistry, TXTParser

# Create registry and register parsers
registry = ParserRegistry()
registry.register(TXTParser())

# Get parser for file type
parser = registry.get_parser(".txt")

# Extract text
chunks = parser.parse("document.txt")

# Access extracted content
for chunk in chunks:
    print(f"Text: {chunk.text}")
    print(f"Metadata: {chunk.metadata}")
```

## Supported File Types

| Format | Extensions            | Status       | Notes                     |
| ------ | --------------------- | ------------ | ------------------------- |
| Text   | .txt, .md, .csv, .log | ✅ Supported | Full file as single chunk |
| PDF    | .pdf                  | ✅ Supported | One chunk per page        |
| DOCX   | .docx                 | ✅ Supported | Paragraphs and table rows |

## Architecture

### BaseParser Interface

All parsers implement the `BaseParser` abstract class:

```python
class BaseParser(ABC):
    @property
    @abstractmethod
    def manifest(self) -> ParserManifest:
        """Plugin manifest with supported_types, version, schema."""
        pass

    @abstractmethod
    def parse(self, file_path: str) -> List[ParsedChunk]:
        """Extract text and metadata from file."""
        pass

    def health_check(self) -> bool:
        """Verify parser dependencies are available."""
        return True
```

### Data Models

**ParsedChunk**: Represents extracted text with positional information

- `text`: Extracted content
- `span_start`: Character offset start
- `span_end`: Character offset end
- `metadata`: Parser-specific metadata

**ParserManifest**: Plugin registration information

- `name`: Unique parser identifier
- `version`: Semantic version
- `supported_types`: List of file extensions
- `dependencies`: Required packages

## Audit Logging

All extraction operations emit audit events:

- `extractor.invoked`: Parser started
- `extractor.succeeded`: Extraction successful
- `extractor.failed`: Extraction failed
- `parser.registered`: Plugin registered
- `parser.health_check`: Health check performed

Events include:

- Parser name and version
- File path and size
- Processing time
- Outcome and error messages
- Character/chunk counts

## Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov

# Run specific test file
poetry run pytest tests/test_registry.py -v
```

## Examples

See `examples/` directory for:

- `basic_usage.py`: Simple TXT extraction example
- `all_parsers.py`: Demonstrates all three parsers (TXT, PDF, DOCX)
- `batch_processing.py`: Process multiple documents
- `custom_parser.py`: How to create your own custom parser

## Development

### Adding a New Parser

1. Create parser class implementing `BaseParser`
2. Define manifest with supported types
3. Implement `parse()` method
4. Add tests in `tests/parsers/`
5. Register in `parsers/__init__.py`

Example:

```python
from gundy_ai.extractors import BaseParser, ParsedChunk, ParserManifest

class MyParser(BaseParser):
    @property
    def manifest(self) -> ParserManifest:
        return ParserManifest(
            name="my_parser",
            version="1.0.0",
            supported_types=[".xyz"]
        )

    def parse(self, file_path: str) -> list[ParsedChunk]:
        # Implementation here
        pass
```

## Requirements

- Python >=3.11,<3.13
- pydantic >=2.5,<3.0
- structlog >=23.2,<25.0
- pypdf >=3.0,<5.0 (for PDF support)
- python-docx >=1.0,<2.0 (for DOCX support)

## License

See main ai-utils repository.

## Contributing

Follow the project guidelines in `.cursorrules` at repository root.
