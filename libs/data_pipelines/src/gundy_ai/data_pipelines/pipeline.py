"""Pipeline orchestration for data processing workflows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

import structlog

from .base import BaseProcessor, ProcessingResult
from .embeddings import EmbeddedDocument

logger = structlog.get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class PipelineStage(Enum):
    """Pipeline stage enumeration."""

    DOCUMENT_EXTRACTION = "document_extraction"
    TEXT_CHUNKING = "text_chunking"
    EMBEDDING_GENERATION = "embedding_generation"
    STORAGE = "storage"
    INDEXING = "indexing"


@dataclass
class PipelineConfig:
    """Configuration for data processing pipeline."""

    name: str
    stages: list[PipelineStage]
    max_concurrent_documents: int = 5
    retry_failed_stages: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineResult:
    """Result of pipeline execution."""

    success: bool
    processed_count: int
    failed_count: int
    results: list[ProcessingResult[Any]]
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: int = 0

    def get_success_rate(self) -> float:
        """Get success rate as percentage."""
        total = self.processed_count + self.failed_count
        if total == 0:
            return 0.0
        return (self.processed_count / total) * 100


class DataPipeline(Generic[T, R]):
    """Orchestrates data processing through multiple stages."""

    def __init__(self, config: PipelineConfig):
        """Initialize data pipeline."""
        self.config = config
        self.logger = logger.bind(pipeline=config.name)
        self.stages: dict[PipelineStage, BaseProcessor[Any, Any]] = {}

    def add_stage(
        self, stage: PipelineStage, processor: BaseProcessor[Any, Any]
    ) -> None:
        """Add a processing stage to the pipeline."""
        self.stages[stage] = processor
        self.logger.info(
            "pipeline.stage.added", stage=stage.value, processor=processor.config.name
        )

    async def process_batch(self, inputs: list[T]) -> PipelineResult:
        """Process a batch of inputs through the pipeline."""
        start_time = asyncio.get_event_loop().time()

        self.logger.info("pipeline.batch.start", input_count=len(inputs))

        # Process documents concurrently
        semaphore = asyncio.Semaphore(self.config.max_concurrent_documents)
        tasks = [self._process_single(semaphore, input_data) for input_data in inputs]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_results = []
        failed_results = []

        for result in results:
            if isinstance(result, Exception):
                failed_results.append(
                    ProcessingResult(
                        success=False, error=f"Pipeline execution error: {str(result)}"
                    )
                )
            elif isinstance(result, ProcessingResult):
                if result.success:
                    successful_results.append(result)
                else:
                    failed_results.append(result)
            else:
                failed_results.append(
                    ProcessingResult(success=False, error="Unknown result type")
                )

        execution_time_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

        pipeline_result = PipelineResult(
            success=len(failed_results) == 0,
            processed_count=len(successful_results),
            failed_count=len(failed_results),
            results=successful_results + failed_results,
            metadata={
                "pipeline_name": self.config.name,
                "total_inputs": len(inputs),
                "stages_used": [stage.value for stage in self.config.stages],
            },
            execution_time_ms=execution_time_ms,
        )

        self.logger.info(
            "pipeline.batch.completed",
            success_count=len(successful_results),
            failed_count=len(failed_results),
            execution_time_ms=execution_time_ms,
        )

        return pipeline_result

    async def _process_single(
        self, semaphore: asyncio.Semaphore, input_data: T
    ) -> ProcessingResult[R]:
        """Process a single input through all pipeline stages."""
        async with semaphore:
            current_data = input_data

            for stage in self.config.stages:
                if stage not in self.stages:
                    return ProcessingResult(
                        success=False, error=f"Stage {stage.value} not configured"
                    )

                processor = self.stages[stage]

                self.logger.debug(
                    "pipeline.stage.processing",
                    stage=stage.value,
                    processor=processor.config.name,
                )

                result = await processor.process_with_retry(current_data)

                if not result.success:
                    if self.config.retry_failed_stages:
                        self.logger.warning(
                            "pipeline.stage.failed",
                            stage=stage.value,
                            error=result.error,
                        )
                        # Could implement retry logic here
                    return result

                current_data = result.data

            return ProcessingResult(
                success=True, data=current_data, metadata={"pipeline": self.config.name}
            )


class DocumentProcessingPipeline(DataPipeline[str, EmbeddedDocument]):
    """Specialized pipeline for document processing."""

    def __init__(self, config: PipelineConfig):
        """Initialize document processing pipeline."""
        super().__init__(config)

        # Validate required stages
        required_stages = {
            PipelineStage.DOCUMENT_EXTRACTION,
            PipelineStage.TEXT_CHUNKING,
            PipelineStage.EMBEDDING_GENERATION,
        }

        if not required_stages.issubset(set(config.stages)):
            missing = required_stages - set(config.stages)
            raise ValueError(f"Missing required stages: {[s.value for s in missing]}")

    async def process_documents(self, file_paths: list[str]) -> PipelineResult:
        """Process a list of document files."""
        return await self.process_batch(file_paths)

    async def process_single_document(
        self, file_path: str
    ) -> ProcessingResult[EmbeddedDocument]:
        """Process a single document file."""
        result = await self.process_batch([file_path])

        if result.results:
            return result.results[0]
        else:
            return ProcessingResult(success=False, error="No results from pipeline")


def create_default_document_pipeline(
    embedding_config: dict[str, Any], chunk_size: int = 1000, chunk_overlap: int = 200
) -> DocumentProcessingPipeline:
    """Create a default document processing pipeline."""
    from .document import (
        DocumentProcessor,
        TextChunker,
        ProcessorConfig,
        ChunkingStrategy,
    )
    from .embeddings import EmbeddingProcessor, EmbeddingConfig, EmbeddingModel

    # Create pipeline configuration
    pipeline_config = PipelineConfig(
        name="default_document_pipeline",
        stages=[
            PipelineStage.DOCUMENT_EXTRACTION,
            PipelineStage.TEXT_CHUNKING,
            PipelineStage.EMBEDDING_GENERATION,
        ],
    )

    # Create pipeline
    pipeline = DocumentProcessingPipeline(pipeline_config)

    # Add document processor
    doc_processor = DocumentProcessor(
        ProcessorConfig(name="document_processor", max_retries=3, timeout_seconds=300)
    )

    # Add chunker
    chunker = TextChunker(
        ProcessorConfig(name="text_chunker", max_retries=2, timeout_seconds=60),
        strategy=ChunkingStrategy.FIXED_SIZE,
        chunk_size=chunk_size,
        overlap=chunk_overlap,
    )

    # Add embedding processor
    embedding_processor = EmbeddingProcessor(
        ProcessorConfig(name="embedding_processor", max_retries=3, timeout_seconds=600),
        EmbeddingConfig(
            model=EmbeddingModel(
                embedding_config.get("model", "text-embedding-3-small")
            ),
            api_key=embedding_config.get("api_key"),
            base_url=embedding_config.get("base_url"),
            max_batch_size=embedding_config.get("max_batch_size", 100),
            embedding_dimensions=embedding_config.get("embedding_dimensions"),
        ),
    )

    # Add stages to pipeline
    pipeline.add_stage(PipelineStage.DOCUMENT_EXTRACTION, doc_processor)
    pipeline.add_stage(PipelineStage.TEXT_CHUNKING, chunker)
    pipeline.add_stage(PipelineStage.EMBEDDING_GENERATION, embedding_processor)

    return pipeline
