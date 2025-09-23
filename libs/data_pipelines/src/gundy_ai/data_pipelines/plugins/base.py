"""Base classes for the plugin system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""

    name: str
    version: str
    description: str
    author: str
    category: str  # "parser", "chunker", "output", "processor"
    dependencies: List[str] = None
    config_schema: Dict[str, Any] = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.config_schema is None:
            self.config_schema = {}


class PluginBase(ABC):
    """Abstract base class for all plugins."""

    def __init__(self, config: Dict[str, Any] = None):
        """Initialize plugin with configuration."""
        self.config = config or {}
        self.logger = logger.bind(plugin=self.__class__.__name__)

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        pass

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        pass

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate plugin configuration against schema."""
        # Basic validation - can be overridden for more complex validation
        schema = self.metadata.config_schema
        if not schema:
            return True

        for key, spec in schema.items():
            if spec.get("required", False) and key not in config:
                self.logger.error("missing_required_config", key=key)
                return False

            if key in config:
                expected_type = spec.get("type")
                if expected_type and not isinstance(config[key], expected_type):
                    self.logger.error(
                        "invalid_config_type",
                        key=key,
                        expected=expected_type.__name__,
                        actual=type(config[key]).__name__,
                    )
                    return False

        return True


class ParserPlugin(PluginBase):
    """Base class for parser plugins."""

    @abstractmethod
    async def can_parse(self, file_path: str, metadata: Dict[str, Any] = None) -> bool:
        """Check if this parser can handle the given file."""
        pass

    @abstractmethod
    async def parse(self, file_path: str, **kwargs: Any) -> Any:
        """Parse the file and return a PDFParsingResult or similar."""
        pass

    @property
    def supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return []

    @property
    def supported_mime_types(self) -> List[str]:
        """Get list of supported MIME types."""
        return []


class ChunkerPlugin(PluginBase):
    """Base class for chunker plugins."""

    @abstractmethod
    async def chunk(self, document: Any, **kwargs: Any) -> Any:
        """Chunk the document and return a ChunkingResult."""
        pass

    @property
    def strategy_name(self) -> str:
        """Get the name of this chunking strategy."""
        return self.metadata.name


class OutputPlugin(PluginBase):
    """Base class for output format plugins."""

    @abstractmethod
    async def write_document(
        self, document: Any, output_path: str, **kwargs: Any
    ) -> Any:
        """Write a single document."""
        pass

    @abstractmethod
    async def write_documents(
        self, documents: List[Any], output_path: str, **kwargs: Any
    ) -> Any:
        """Write multiple documents."""
        pass

    @property
    def format_name(self) -> str:
        """Get the name of this output format."""
        return self.metadata.name

    @property
    def file_extension(self) -> str:
        """Get the file extension for this format."""
        return f".{self.metadata.name.lower()}"


class ProcessorPlugin(PluginBase):
    """Base class for general processor plugins."""

    @abstractmethod
    async def process(self, input_data: Any, **kwargs: Any) -> Any:
        """Process the input data."""
        pass

    @property
    def processor_type(self) -> str:
        """Get the type of processor."""
        return self.metadata.name
