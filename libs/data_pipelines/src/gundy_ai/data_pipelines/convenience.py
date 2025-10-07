"""Convenience imports for common use cases."""

# Most commonly used components for typical workflows
from .unified_document import DocumentProcessor
from .enhanced_chunker import EnhancedTextChunker
from .document import DocumentType, ChunkingStrategy, ProcessedDocument, TextChunk
from .base import ProcessorConfig, ProcessingResult
from .config import (
    configure_for_openai,
    configure_for_claude,
    configure_for_local_llm,
    get_config,
    set_config,
)
from .chunkers import ChunkSplittingFilter

# Backward compatibility
from .unified_document import EnhancedDocumentProcessor

__all__ = [
    # Core processing
    "DocumentProcessor",
    "EnhancedTextChunker",
    "ProcessorConfig",
    "ProcessingResult",
    # Document types and data
    "DocumentType",
    "ChunkingStrategy",
    "ProcessedDocument",
    "TextChunk",
    # Configuration (most important)
    "configure_for_openai",
    "configure_for_claude",
    "configure_for_local_llm",
    "get_config",
    "set_config",
    # Utilities
    "ChunkSplittingFilter",
    # Backward compatibility
    "EnhancedDocumentProcessor",
]
