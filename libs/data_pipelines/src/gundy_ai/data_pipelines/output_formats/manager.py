"""Output format manager for coordinating different writers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog

from ..document import ProcessedDocument
from .base import OutputFormat, OutputResult, OutputWriter
from .json_writer import JSONWriter, NDJSONWriter
from .parquet_writer import ParquetWriter

logger = structlog.get_logger(__name__)


class OutputManager:
    """Manager for handling multiple output formats."""

    def __init__(self):
        """Initialize output manager with default writers."""
        self.writers: dict[OutputFormat, OutputWriter] = {
            OutputFormat.JSON: JSONWriter(),
            OutputFormat.NDJSON: NDJSONWriter(),
            OutputFormat.PARQUET: ParquetWriter(),
        }

    def register_writer(self, format_type: OutputFormat, writer: OutputWriter) -> None:
        """Register a custom writer for a format."""
        self.writers[format_type] = writer

    def get_writer(self, format_type: OutputFormat) -> OutputWriter:
        """Get writer for specified format."""
        if format_type not in self.writers:
            raise ValueError(f"No writer registered for format: {format_type}")
        return self.writers[format_type]

    async def write_document(
        self,
        document: ProcessedDocument,
        output_path: str | Path,
        format_type: OutputFormat | str,
        **kwargs: Any,
    ) -> OutputResult:
        """Write a single document in the specified format.

        Args:
            document: The processed document to write
            output_path: Path where to write the output
            format_type: Output format to use
            **kwargs: Additional format-specific options

        Returns:
            OutputResult with operation details
        """
        # Normalize format type
        if isinstance(format_type, str):
            format_type = OutputFormat(format_type.lower())

        writer = self.get_writer(format_type)
        return await writer.write_document(document, output_path, **kwargs)

    async def write_documents(
        self,
        documents: list[ProcessedDocument],
        output_path: str | Path,
        format_type: OutputFormat | str,
        **kwargs: Any,
    ) -> OutputResult:
        """Write multiple documents in the specified format.

        Args:
            documents: List of processed documents to write
            output_path: Path where to write the output
            format_type: Output format to use
            **kwargs: Additional format-specific options

        Returns:
            OutputResult with operation details
        """
        # Normalize format type
        if isinstance(format_type, str):
            format_type = OutputFormat(format_type.lower())

        writer = self.get_writer(format_type)
        return await writer.write_documents(documents, output_path, **kwargs)

    async def write_multiple_formats(
        self,
        documents: list[ProcessedDocument],
        output_directory: str | Path,
        formats: list[OutputFormat | str],
        base_filename: str = "output",
        **kwargs: Any,
    ) -> dict[OutputFormat, OutputResult]:
        """Write documents in multiple formats simultaneously.

        Args:
            documents: List of processed documents to write
            output_directory: Directory where to write outputs
            formats: List of output formats to generate
            base_filename: Base filename (extensions will be added automatically)
            **kwargs: Additional format-specific options

        Returns:
            Dictionary mapping formats to their OutputResults
        """
        output_dir = Path(output_directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}

        # File extensions for each format
        extensions = {
            OutputFormat.JSON: ".json",
            OutputFormat.NDJSON: ".ndjson",
            OutputFormat.PARQUET: ".parquet",
        }

        for format_type in formats:
            # Normalize format type
            if isinstance(format_type, str):
                format_type = OutputFormat(format_type.lower())

            try:
                # Generate output path with appropriate extension
                extension = extensions.get(format_type, f".{format_type.value}")
                output_path = output_dir / f"{base_filename}{extension}"

                # Write in this format
                result = await self.write_documents(
                    documents, output_path, format_type, **kwargs
                )
                results[format_type] = result

                logger.info(
                    "multi_format_write_success",
                    format=format_type.value,
                    output_path=str(output_path),
                    success=result.success,
                )

            except Exception as e:
                logger.error(
                    "multi_format_write_error", format=format_type.value, error=str(e)
                )
                results[format_type] = OutputResult(
                    success=False,
                    format=format_type,
                    error=f"Failed to write {format_type.value}: {str(e)}",
                )

        return results

    def get_supported_formats(self) -> list[OutputFormat]:
        """Get list of supported output formats."""
        return list(self.writers.keys())

    def get_format_info(self, format_type: OutputFormat) -> dict[str, Any]:
        """Get information about a specific format."""
        if format_type not in self.writers:
            raise ValueError(f"Format not supported: {format_type}")

        writer = self.writers[format_type]

        return {
            "format": format_type.value,
            "writer_class": writer.__class__.__name__,
            "description": self._get_format_description(format_type),
            "use_cases": self._get_format_use_cases(format_type),
            "config": writer.config,
        }

    def _get_format_description(self, format_type: OutputFormat) -> str:
        """Get description for a format."""
        descriptions = {
            OutputFormat.JSON: "Human-readable JSON format with full document structure",
            OutputFormat.NDJSON: "Newline-delimited JSON for streaming and big data processing",
            OutputFormat.PARQUET: "Columnar format optimized for analytics and compression",
        }
        return descriptions.get(format_type, f"Output format: {format_type.value}")

    def _get_format_use_cases(self, format_type: OutputFormat) -> list[str]:
        """Get use cases for a format."""
        use_cases = {
            OutputFormat.JSON: [
                "API responses",
                "Configuration files",
                "Small to medium datasets",
                "Human inspection",
            ],
            OutputFormat.NDJSON: [
                "Streaming data processing",
                "Log file analysis",
                "Large dataset processing",
                "ETL pipelines",
            ],
            OutputFormat.PARQUET: [
                "Data analytics",
                "Data warehousing",
                "Machine learning datasets",
                "Long-term storage",
            ],
        }
        return use_cases.get(format_type, ["General purpose output"])
