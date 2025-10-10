"""Data models for document extraction."""

from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class ParsedChunk(BaseModel):
    """A chunk of extracted text with metadata.

    Represents a portion of a document that has been extracted,
    with positional information and optional metadata.
    """

    text: str = Field(description="Extracted text content")
    span_start: int = Field(
        description="Character offset start position in original document"
    )
    span_end: int = Field(
        description="Character offset end position in original document"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parser-specific metadata (e.g., page number, section, style)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "text": "This is extracted text from a document.",
                "span_start": 0,
                "span_end": 40,
                "metadata": {"page": 1, "parser": "txt"},
            }
        }
    )


class ParserManifest(BaseModel):
    """Plugin manifest describing parser capabilities.

    Used to identify and validate parser plugins at registration time.
    """

    name: str = Field(description="Unique parser name (e.g., 'txt', 'pdf', 'docx')")
    version: str = Field(description="Parser version (semantic versioning)")
    supported_types: List[str] = Field(
        description="File extensions supported (e.g., ['.txt', '.md'])"
    )
    schema_version: str = Field(
        default="1.0", description="Manifest schema version for compatibility checking"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Required dependencies with versions (e.g., ['pypdf>=3.0'])",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "txt",
                "version": "1.0.0",
                "supported_types": [".txt", ".md"],
                "schema_version": "1.0",
                "dependencies": [],
            }
        }
    )
