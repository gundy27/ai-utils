"""Centralized configuration for data pipelines."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ChunkingConfig:
    """Configuration for text chunking strategies."""

    # Token-based settings (for LLM compatibility)
    max_tokens: int = 8192  # Hard limit (OpenAI GPT-4/3.5)
    target_tokens: int = 4000  # Preferred chunk size
    overlap_tokens: int = 200  # Overlap between chunks

    # Character-based settings (fallback/legacy)
    max_chunk_size: int = 4000  # Maximum characters per chunk
    min_chunk_size: int = 100  # Minimum characters per chunk
    overlap_size: int = 200  # Character overlap

    # Tokenizer settings
    encoding_name: str = "cl100k_base"  # GPT-4/3.5 encoding

    # Structure preservation
    preserve_sentences: bool = True
    preserve_paragraphs: bool = True

    # Strategy-specific settings
    semantic_similarity_threshold: float = 0.7
    structure_aware_min_section_size: int = 50

    @classmethod
    def from_env(cls) -> ChunkingConfig:
        """Create configuration from environment variables."""
        return cls(
            max_tokens=int(os.getenv("CHUNKING_MAX_TOKENS", "8192")),
            target_tokens=int(os.getenv("CHUNKING_TARGET_TOKENS", "4000")),
            overlap_tokens=int(os.getenv("CHUNKING_OVERLAP_TOKENS", "200")),
            max_chunk_size=int(os.getenv("CHUNKING_MAX_CHUNK_SIZE", "4000")),
            min_chunk_size=int(os.getenv("CHUNKING_MIN_CHUNK_SIZE", "100")),
            overlap_size=int(os.getenv("CHUNKING_OVERLAP_SIZE", "200")),
            encoding_name=os.getenv("CHUNKING_ENCODING", "cl100k_base"),
            preserve_sentences=os.getenv("CHUNKING_PRESERVE_SENTENCES", "true").lower()
            == "true",
            preserve_paragraphs=os.getenv(
                "CHUNKING_PRESERVE_PARAGRAPHS", "true"
            ).lower()
            == "true",
            semantic_similarity_threshold=float(
                os.getenv("CHUNKING_SEMANTIC_THRESHOLD", "0.7")
            ),
            structure_aware_min_section_size=int(
                os.getenv("CHUNKING_MIN_SECTION_SIZE", "50")
            ),
        )

    @classmethod
    def for_openai(cls, model: str = "gpt-4") -> ChunkingConfig:
        """Create configuration optimized for OpenAI models."""
        if model in ["gpt-4", "gpt-3.5-turbo"]:
            return cls(
                max_tokens=8192,
                target_tokens=4000,
                overlap_tokens=200,
                encoding_name="cl100k_base",
            )
        elif model.startswith("gpt-3"):
            return cls(
                max_tokens=4096,
                target_tokens=2000,
                overlap_tokens=100,
                encoding_name="p50k_base",
            )
        else:
            return cls()

    @classmethod
    def for_claude(cls) -> ChunkingConfig:
        """Create configuration optimized for Claude."""
        return cls(
            max_tokens=100000,  # Claude's large context window
            target_tokens=8000,  # Larger chunks for efficiency
            overlap_tokens=400,  # More overlap for better context
            encoding_name="cl100k_base",  # Use GPT-4 encoding as approximation
        )

    @classmethod
    def for_local_llm(cls, context_window: int = 4096) -> ChunkingConfig:
        """Create configuration for local/open-source LLMs."""
        return cls(
            max_tokens=context_window,
            target_tokens=context_window // 2,
            overlap_tokens=context_window // 20,
            encoding_name="cl100k_base",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "max_tokens": self.max_tokens,
            "target_tokens": self.target_tokens,
            "overlap_tokens": self.overlap_tokens,
            "max_chunk_size": self.max_chunk_size,
            "min_chunk_size": self.min_chunk_size,
            "overlap_size": self.overlap_size,
            "encoding_name": self.encoding_name,
            "preserve_sentences": self.preserve_sentences,
            "preserve_paragraphs": self.preserve_paragraphs,
            "semantic_similarity_threshold": self.semantic_similarity_threshold,
            "structure_aware_min_section_size": self.structure_aware_min_section_size,
        }


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""

    # Chunking configuration
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)

    # PDF processing
    pdf_parser_priority: list[str] = field(
        default_factory=lambda: ["pymupdf", "pdfplumber", "pypdf", "ocr_fallback"]
    )
    enable_ocr_fallback: bool = True
    ocr_confidence_threshold: float = 0.6
    min_text_extraction_ratio: float = 0.1

    # Text cleaning
    enable_text_cleaning: bool = True
    text_cleaning_strategy: str = "auto"

    # Output settings
    default_output_format: str = "json"
    include_metadata: bool = True

    # Performance settings
    max_concurrent_operations: int = 10
    timeout_seconds: int = 300

    @classmethod
    def from_env(cls) -> ProcessingConfig:
        """Create configuration from environment variables."""
        return cls(
            chunking=ChunkingConfig.from_env(),
            pdf_parser_priority=os.getenv(
                "PDF_PARSER_PRIORITY", "pymupdf,pdfplumber,pypdf,ocr_fallback"
            ).split(","),
            enable_ocr_fallback=os.getenv("ENABLE_OCR_FALLBACK", "true").lower()
            == "true",
            ocr_confidence_threshold=float(
                os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.6")
            ),
            min_text_extraction_ratio=float(
                os.getenv("MIN_TEXT_EXTRACTION_RATIO", "0.1")
            ),
            enable_text_cleaning=os.getenv("ENABLE_TEXT_CLEANING", "true").lower()
            == "true",
            text_cleaning_strategy=os.getenv("TEXT_CLEANING_STRATEGY", "auto"),
            default_output_format=os.getenv("DEFAULT_OUTPUT_FORMAT", "json"),
            include_metadata=os.getenv("INCLUDE_METADATA", "true").lower() == "true",
            max_concurrent_operations=int(os.getenv("MAX_CONCURRENT_OPERATIONS", "10")),
            timeout_seconds=int(os.getenv("TIMEOUT_SECONDS", "300")),
        )

    @classmethod
    def for_llm(cls, llm_provider: str, model: str = "") -> ProcessingConfig:
        """Create configuration optimized for specific LLM providers."""
        if llm_provider.lower() == "openai":
            chunking_config = ChunkingConfig.for_openai(model)
        elif llm_provider.lower() == "claude":
            chunking_config = ChunkingConfig.for_claude()
        elif llm_provider.lower() == "local":
            context_window = int(model) if model.isdigit() else 4096
            chunking_config = ChunkingConfig.for_local_llm(context_window)
        else:
            chunking_config = ChunkingConfig()

        return cls(chunking=chunking_config)


# Global configuration instance
_global_config: Optional[ProcessingConfig] = None


def get_config() -> ProcessingConfig:
    """Get the global configuration instance."""
    global _global_config
    if _global_config is None:
        _global_config = ProcessingConfig.from_env()
    return _global_config


def set_config(config: ProcessingConfig) -> None:
    """Set the global configuration instance."""
    global _global_config
    _global_config = config
    logger.info("global_config_updated", config_summary=_summarize_config(config))


def configure_for_llm(llm_provider: str, model: str = "") -> ProcessingConfig:
    """Configure the library for a specific LLM provider."""
    config = ProcessingConfig.for_llm(llm_provider, model)
    set_config(config)
    return config


def reset_config() -> None:
    """Reset configuration to default values."""
    global _global_config
    _global_config = None
    logger.info("global_config_reset")


def _summarize_config(config: ProcessingConfig) -> Dict[str, Any]:
    """Create a summary of configuration for logging."""
    return {
        "max_tokens": config.chunking.max_tokens,
        "target_tokens": config.chunking.target_tokens,
        "encoding": config.chunking.encoding_name,
        "ocr_enabled": config.enable_ocr_fallback,
        "text_cleaning": config.enable_text_cleaning,
    }


# Convenience functions for common configurations
def configure_for_openai(model: str = "gpt-4") -> ProcessingConfig:
    """Configure for OpenAI models."""
    return configure_for_llm("openai", model)


def configure_for_claude() -> ProcessingConfig:
    """Configure for Claude."""
    return configure_for_llm("claude")


def configure_for_local_llm(context_window: int = 4096) -> ProcessingConfig:
    """Configure for local/open-source LLMs."""
    return configure_for_llm("local", str(context_window))


# Quick configuration presets
OPENAI_GPT4_CONFIG = ProcessingConfig.for_llm("openai", "gpt-4")
OPENAI_GPT35_CONFIG = ProcessingConfig.for_llm("openai", "gpt-3.5-turbo")
CLAUDE_CONFIG = ProcessingConfig.for_llm("claude")
LOCAL_4K_CONFIG = ProcessingConfig.for_llm("local", "4096")
LOCAL_8K_CONFIG = ProcessingConfig.for_llm("local", "8192")
LOCAL_16K_CONFIG = ProcessingConfig.for_llm("local", "16384")
