"""Enhanced text chunker with multiple strategies."""

from __future__ import annotations

import time
from typing import Any

import structlog

from .base import BaseProcessor, ProcessingResult, ProcessorConfig
from .chunkers import (
    BaseChunker,
    SemanticChunker,
    StructureAwareChunker,
    TokenAwareChunker,
)
from .document import ChunkingStrategy, ProcessedDocument, TextChunker
from .audit_integration import ProcessingAuditHook
from .config import ChunkingConfig, get_config

logger = structlog.get_logger(__name__)


class EnhancedTextChunker(BaseProcessor[ProcessedDocument, ProcessedDocument]):
    """Enhanced text chunker with multiple chunking strategies."""

    def __init__(
        self,
        config: ProcessorConfig,
        strategy: ChunkingStrategy | str = ChunkingStrategy.SEMANTIC,
        chunk_size: int | None = None,
        overlap: int | None = None,
        chunking_config: ChunkingConfig | None = None,
        audit_hook: Any | None = None,
        **strategy_kwargs: Any,
    ):
        """Initialize enhanced text chunker.

        Args:
            config: Processor configuration
            strategy: Chunking strategy to use
            chunk_size: Target chunk size (None to use global config)
            overlap: Overlap between chunks (None to use global config)
            chunking_config: Custom chunking configuration (None to use global config)
            audit_hook: Optional audit hook for tracking operations
            **strategy_kwargs: Additional arguments for specific strategies
        """
        super().__init__(config)

        # Get chunking configuration
        if chunking_config is None:
            chunking_config = get_config().chunking

        # Normalize strategy
        if isinstance(strategy, str):
            if strategy == "semantic":
                self.strategy = ChunkingStrategy.SEMANTIC
            elif strategy == "structure_aware":
                self.strategy = ChunkingStrategy.STRUCTURE_AWARE
            elif strategy == "token_aware":
                self.strategy = ChunkingStrategy.TOKEN_AWARE
            else:
                self.strategy = ChunkingStrategy(strategy)
        else:
            self.strategy = strategy

        # Use provided values or fall back to configuration
        if self.strategy == ChunkingStrategy.TOKEN_AWARE:
            self.chunk_size = chunk_size or chunking_config.target_tokens
            self.overlap = overlap or chunking_config.overlap_tokens
        else:
            self.chunk_size = chunk_size or chunking_config.max_chunk_size
            self.overlap = overlap or chunking_config.overlap_size

        self.chunking_config = chunking_config
        self.strategy_kwargs = strategy_kwargs

        # Initialize audit hook
        self.audit_hook = ProcessingAuditHook(audit_hook)

        # Initialize chunker based on strategy
        self.chunker = self._create_chunker()

    def _create_chunker(self) -> BaseChunker | TextChunker:
        """Create appropriate chunker based on strategy."""
        if self.strategy == ChunkingStrategy.SEMANTIC:
            return SemanticChunker(
                max_chunk_size=self.chunk_size,
                min_chunk_size=max(50, self.chunk_size // 10),
                **self.strategy_kwargs,
            )
        elif self.strategy == ChunkingStrategy.STRUCTURE_AWARE:
            return StructureAwareChunker(
                max_chunk_size=self.chunk_size,
                min_chunk_size=max(50, self.chunk_size // 10),
                **self.strategy_kwargs,
            )
        elif self.strategy == ChunkingStrategy.TOKEN_AWARE:
            return TokenAwareChunker(
                max_tokens=self.chunking_config.max_tokens,
                target_tokens=self.chunk_size,
                overlap_tokens=self.overlap,
                encoding_name=self.chunking_config.encoding_name,
                preserve_sentences=self.chunking_config.preserve_sentences,
                preserve_paragraphs=self.chunking_config.preserve_paragraphs,
                **self.strategy_kwargs,
            )
        else:
            # Use original TextChunker for other strategies
            return TextChunker(
                config=self.config,
                strategy=self.strategy,
                chunk_size=self.chunk_size,
                overlap=self.overlap,
            )

    def validate_input(self, input_data: ProcessedDocument) -> bool:
        """Validate input is a processed document."""
        return isinstance(input_data, ProcessedDocument)

    async def process(
        self, document: ProcessedDocument
    ) -> ProcessingResult[ProcessedDocument]:
        """Chunk the document text using the configured strategy."""
        start_time = time.time()

        try:
            if isinstance(self.chunker, BaseChunker):
                # Use new chunker interface
                result = await self.chunker.chunk(document)

                if result.success:
                    # Update document with chunks
                    document.chunks = result.chunks

                    processing_time = (time.time() - start_time) * 1000

                    # Log chunking operation if we have a parent event ID
                    parent_event_id = document.metadata.custom_metadata.get("event_id")
                    if parent_event_id:
                        avg_chunk_size = (
                            sum(chunk.token_count for chunk in result.chunks)
                            / len(result.chunks)
                            if result.chunks
                            else 0
                        )
                        await self.audit_hook.log_chunking_operation(
                            event_id=parent_event_id,
                            chunking_strategy=str(self.strategy),
                            chunk_count=len(result.chunks),
                            processing_time_ms=processing_time,
                            avg_chunk_size=avg_chunk_size,
                            chunker_metadata=result.metadata,
                        )

                    return ProcessingResult(
                        success=True,
                        data=document,
                        metadata={
                            "chunk_count": len(result.chunks),
                            "strategy": str(self.strategy),
                            "chunk_size": self.chunk_size,
                            "overlap": self.overlap,
                            "processing_time_ms": processing_time,
                            "chunker_metadata": result.metadata,
                        },
                    )
                else:
                    return ProcessingResult(
                        success=False,
                        error=f"Chunking failed: {result.error}",
                        metadata={"strategy": str(self.strategy)},
                    )
            else:
                # Use original TextChunker
                return await self.chunker.process(document)

        except Exception as e:
            self.logger.error(
                "enhanced_chunking_error", error=str(e), strategy=str(self.strategy)
            )
            return ProcessingResult(
                success=False,
                error=f"Enhanced chunking failed: {str(e)}",
                metadata={
                    "strategy": str(self.strategy),
                    "processing_time_ms": (time.time() - start_time) * 1000,
                },
            )
