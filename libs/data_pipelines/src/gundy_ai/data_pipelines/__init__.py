"""Data processing utilities for AI applications.

This library provides comprehensive document processing, text chunking, and pipeline
orchestration capabilities optimized for AI applications, particularly RAG systems.

Quick Start:
    >>> from gundy_ai.data_pipelines import DocumentProcessor, configure_for_openai
    >>>
    >>> # Configure for your LLM
    >>> configure_for_openai("gpt-4")
    >>>
    >>> # Process documents
    >>> processor = DocumentProcessor(ProcessorConfig(name="my_processor"))
    >>> result = await processor.process("document.pdf")

For advanced features, import from specific modules:
    >>> from gundy_ai.data_pipelines.parsers import PyMuPDFParser
    >>> from gundy_ai.data_pipelines.chunkers import SemanticChunker
    >>> from gundy_ai.data_pipelines.output_formats import ParquetWriter
"""

# Core components (most commonly used)
from .base import (
    BaseProcessor,
    ProcessingResult,
    ProcessorConfig,
)
from .document import (
    DocumentType,
    DocumentMetadata,
    ProcessedDocument,
    TextChunk,
    TextChunker,
    ChunkingStrategy,
)
from .unified_document import DocumentProcessor, EnhancedDocumentProcessor
from .enhanced_chunker import EnhancedTextChunker

# Essential chunking components
from .chunkers import (
    ChunkSplittingFilter,
    SemanticChunker,
    StructureAwareChunker,
    TokenAwareChunker,
)

# Configuration system (very important for usability)
from .config import (
    ChunkingConfig,
    ProcessingConfig,
    get_config,
    set_config,
    configure_for_llm,
    configure_for_openai,
    configure_for_claude,
    configure_for_local_llm,
    reset_config,
    # Presets
    OPENAI_GPT4_CONFIG,
    OPENAI_GPT35_CONFIG,
    CLAUDE_CONFIG,
    LOCAL_4K_CONFIG,
    LOCAL_8K_CONFIG,
    LOCAL_16K_CONFIG,
)

# Pipeline orchestration
from .pipeline import (
    DataPipeline,
    PipelineStage,
    PipelineConfig,
)

# Essential exports for most users
__all__ = [
    # Core processing (essential)
    "DocumentProcessor",
    "EnhancedTextChunker",
    "ProcessorConfig",
    "ProcessingResult",
    # Document types and data (essential)
    "DocumentType",
    "DocumentMetadata",
    "ProcessedDocument",
    "TextChunk",
    "ChunkingStrategy",
    # Configuration (very important)
    "configure_for_openai",
    "configure_for_claude",
    "configure_for_local_llm",
    "get_config",
    "set_config",
    "ChunkingConfig",
    "ProcessingConfig",
    # Common chunking utilities
    "ChunkSplittingFilter",
    "SemanticChunker",
    "StructureAwareChunker",
    "TokenAwareChunker",
    # Pipeline orchestration
    "DataPipeline",
    "PipelineStage",
    "PipelineConfig",
    # Base classes (for advanced users)
    "BaseProcessor",
    "TextChunker",
    # Backward compatibility
    "EnhancedDocumentProcessor",
    # Configuration presets
    "OPENAI_GPT4_CONFIG",
    "OPENAI_GPT35_CONFIG",
    "CLAUDE_CONFIG",
    "LOCAL_4K_CONFIG",
    "LOCAL_8K_CONFIG",
    "LOCAL_16K_CONFIG",
    # Advanced imports available via submodules:
    # - gundy_ai.data_pipelines.parsers (PDF parsers, OCR)
    # - gundy_ai.data_pipelines.text_cleaning (text cleaners)
    # - gundy_ai.data_pipelines.output_formats (JSON, Parquet writers)
    # - gundy_ai.data_pipelines.plugins (plugin system)
    # - gundy_ai.data_pipelines.metrics (observability)
    # - gundy_ai.data_pipelines.audit_integration (audit logging)
]


# Convenience function for quick setup
def quick_setup(
    llm_provider: str = "openai", model: str = "gpt-4"
) -> DocumentProcessor:
    """Quick setup for common use cases.

    Args:
        llm_provider: LLM provider ("openai", "claude", "local")
        model: Model name or context window size for local models

    Returns:
        Configured DocumentProcessor ready to use

    Example:
        >>> processor = quick_setup("openai", "gpt-4")
        >>> result = await processor.process("document.pdf")
    """
    if llm_provider.lower() == "openai":
        configure_for_openai(model)
    elif llm_provider.lower() == "claude":
        configure_for_claude()
    elif llm_provider.lower() == "local":
        context_window = int(model) if model.isdigit() else 4096
        configure_for_local_llm(context_window)
    else:
        raise ValueError(f"Unsupported LLM provider: {llm_provider}")

    return DocumentProcessor(
        config=ProcessorConfig(name="quick_setup_processor"),
        pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf", "ocr_fallback"],
        enable_ocr_fallback=True,
        enable_text_cleaning=True,
    )


# Add quick_setup to exports
__all__.append("quick_setup")
