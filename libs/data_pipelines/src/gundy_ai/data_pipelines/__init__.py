"""Data processing utilities for AI applications."""

from .base import (
    BaseProcessor,
    ProcessingResult,
    ProcessingStage,
    ProcessorConfig,
)
from .document import (
    DocumentProcessor,
    DocumentType,
    TextChunk,
    ChunkingStrategy,
)
from .enhanced_document import (
    EnhancedDocumentProcessor,
)
from .enhanced_chunker import (
    EnhancedTextChunker,
)
from .chunkers import (
    BaseChunker,
    ChunkingResult,
    SemanticChunker,
    StructureAwareChunker,
)
from .embeddings import (
    EmbeddingProcessor,
    EmbeddingConfig,
    EmbeddingModel,
)
from .parsers import (
    PDFParser,
    PDFParsingResult,
    PDFPage,
    PDFPlumberParser,
    PyMuPDFParser,
    PyPDFParser,
    OCRFallbackParser,
)
from .pipeline import (
    DataPipeline,
    PipelineStage,
    PipelineConfig,
)
from .text_cleaning import (
    TextCleaner,
    CleaningResult,
    PDFTextCleaner,
    OCRTextCleaner,
    GeneralTextCleaner,
)
from .audit_integration import (
    ProcessingAuditEvent,
    ProcessingAuditHook,
)
from .output_formats import (
    OutputFormat,
    OutputWriter,
    OutputResult,
    OutputManager,
    JSONWriter,
    NDJSONWriter,
    ParquetWriter,
)
from .plugins import (
    PluginRegistry,
    PluginInfo,
    PluginBase,
    ParserPlugin,
    ChunkerPlugin,
    OutputPlugin,
    PluginLoader,
    PluginManager,
)
from .metrics import (
    MetricsCollector,
    ProcessingMetrics,
    MetricsReporter,
    MetricsReport,
    MetricsDashboard,
    AlertManager,
    AlertRule,
    AlertCondition,
)

__all__ = [
    # Base classes
    "BaseProcessor",
    "ProcessingResult",
    "ProcessingStage",
    "ProcessorConfig",
    # Document processing
    "DocumentProcessor",
    "EnhancedDocumentProcessor",
    "DocumentType",
    "TextChunk",
    "ChunkingStrategy",
    # Enhanced chunking
    "EnhancedTextChunker",
    "BaseChunker",
    "ChunkingResult",
    "SemanticChunker",
    "StructureAwareChunker",
    # PDF Parsers
    "PDFParser",
    "PDFParsingResult",
    "PDFPage",
    "PDFPlumberParser",
    "PyMuPDFParser",
    "PyPDFParser",
    "OCRFallbackParser",
    # Embeddings
    "EmbeddingProcessor",
    "EmbeddingConfig",
    "EmbeddingModel",
    # Pipeline orchestration
    "DataPipeline",
    "PipelineStage",
    "PipelineConfig",
    # Text cleaning
    "TextCleaner",
    "CleaningResult",
    "PDFTextCleaner",
    "OCRTextCleaner",
    "GeneralTextCleaner",
    # Audit integration
    "ProcessingAuditEvent",
    "ProcessingAuditHook",
    # Output formats
    "OutputFormat",
    "OutputWriter",
    "OutputResult",
    "OutputManager",
    "JSONWriter",
    "NDJSONWriter",
    "ParquetWriter",
    # Plugin system
    "PluginRegistry",
    "PluginInfo",
    "PluginBase",
    "ParserPlugin",
    "ChunkerPlugin",
    "OutputPlugin",
    "PluginLoader",
    "PluginManager",
    # Metrics and observability
    "MetricsCollector",
    "ProcessingMetrics",
    "MetricsReporter",
    "MetricsReport",
    "MetricsDashboard",
    "AlertManager",
    "AlertRule",
    "AlertCondition",
]
