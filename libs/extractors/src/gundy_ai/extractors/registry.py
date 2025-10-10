"""Plugin registry for managing document parsers."""

from __future__ import annotations

from typing import Dict, List, Optional

import structlog

from .audit import ExtractionEventType, emit_extraction_event
from .base import BaseParser
from .models import ParserManifest

logger = structlog.get_logger(__name__)


class ParserRegistry:
    """Registry for managing parser plugins.

    Provides a centralized way to register, discover, and retrieve
    parsers based on file extensions.

    Example:
        registry = ParserRegistry()
        registry.register(TXTParser())
        parser = registry.get_parser(".txt")
        chunks = parser.parse("document.txt")
    """

    def __init__(self):
        """Initialize empty registry."""
        self._parsers: Dict[str, BaseParser] = {}
        self._extension_map: Dict[str, str] = {}
        logger.info("parser_registry_initialized")

    def register(self, parser: BaseParser) -> None:
        """Register a parser plugin.

        Args:
            parser: Parser instance to register

        Raises:
            ValueError: If parser name already registered or extension conflict
        """
        manifest = parser.manifest

        # Check if parser name already registered
        if manifest.name in self._parsers:
            raise ValueError(
                f"Parser '{manifest.name}' is already registered. "
                f"Use a different name or unregister the existing parser first."
            )

        # Check for extension conflicts
        for ext in manifest.supported_types:
            if ext in self._extension_map:
                existing_parser = self._extension_map[ext]
                raise ValueError(
                    f"Extension '{ext}' is already registered to parser '{existing_parser}'. "
                    f"Cannot register parser '{manifest.name}'."
                )

        # Register parser
        self._parsers[manifest.name] = parser

        # Map extensions to parser name
        for ext in manifest.supported_types:
            self._extension_map[ext] = manifest.name

        logger.info(
            "parser_registered",
            parser_name=manifest.name,
            version=manifest.version,
            supported_types=manifest.supported_types,
        )

        # Emit audit event
        emit_extraction_event(
            event_type=ExtractionEventType.PARSER_REGISTERED,
            parser_name=manifest.name,
            file_path="",  # No specific file for registration
            outcome="success",
            parser_version=manifest.version,
            metadata={
                "supported_types": manifest.supported_types,
                "dependencies": manifest.dependencies,
            },
        )

    def unregister(self, parser_name: str) -> None:
        """Unregister a parser plugin.

        Args:
            parser_name: Name of parser to unregister

        Raises:
            KeyError: If parser not found
        """
        if parser_name not in self._parsers:
            raise KeyError(f"Parser '{parser_name}' not found in registry")

        parser = self._parsers[parser_name]
        manifest = parser.manifest

        # Remove extension mappings
        for ext in manifest.supported_types:
            if ext in self._extension_map and self._extension_map[ext] == parser_name:
                del self._extension_map[ext]

        # Remove parser
        del self._parsers[parser_name]

        logger.info("parser_unregistered", parser_name=parser_name)

    def get_parser(self, file_extension: str) -> Optional[BaseParser]:
        """Get parser for a file extension.

        Args:
            file_extension: File extension (e.g., ".txt", ".pdf")

        Returns:
            Parser instance if found, None otherwise
        """
        # Normalize extension (ensure it starts with .)
        if not file_extension.startswith("."):
            file_extension = f".{file_extension}"

        file_extension = file_extension.lower()

        parser_name = self._extension_map.get(file_extension)
        if parser_name:
            return self._parsers[parser_name]

        logger.warning("no_parser_found", file_extension=file_extension)
        return None

    def get_parser_by_name(self, parser_name: str) -> Optional[BaseParser]:
        """Get parser by its name.

        Args:
            parser_name: Name of parser

        Returns:
            Parser instance if found, None otherwise
        """
        return self._parsers.get(parser_name)

    def list_parsers(self) -> List[ParserManifest]:
        """List all registered parsers.

        Returns:
            List of parser manifests
        """
        return [parser.manifest for parser in self._parsers.values()]

    def get_supported_extensions(self) -> List[str]:
        """Get list of all supported file extensions.

        Returns:
            List of file extensions (e.g., [".txt", ".pdf"])
        """
        return list(self._extension_map.keys())

    def health_check_all(self) -> Dict[str, bool]:
        """Run health checks on all registered parsers.

        Returns:
            Dict mapping parser names to health check results
        """
        results = {}
        for name, parser in self._parsers.items():
            try:
                is_healthy = parser.health_check()
                results[name] = is_healthy

                # Emit audit event
                emit_extraction_event(
                    event_type=ExtractionEventType.PARSER_HEALTH_CHECK,
                    parser_name=name,
                    file_path="",
                    outcome="success" if is_healthy else "failure",
                    parser_version=parser.manifest.version,
                    metadata={"healthy": is_healthy},
                )
            except Exception as e:
                results[name] = False
                logger.error(
                    "parser_health_check_failed",
                    parser_name=name,
                    error=str(e),
                )

        return results

    def __repr__(self) -> str:
        """String representation of registry."""
        return f"ParserRegistry(parsers={len(self._parsers)}, extensions={len(self._extension_map)})"
