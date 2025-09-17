"""Base classes for data processing components."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")
R = TypeVar("R")


class ProcessingStage(Enum):
    """Processing stage enumeration."""

    INITIALIZATION = "initialization"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    ENRICHMENT = "enrichment"
    FINALIZATION = "finalization"


@dataclass
class ProcessorConfig:
    """Base configuration for processors."""

    name: str
    enabled: bool = True
    max_retries: int = 3
    timeout_seconds: int = 300
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingResult(Generic[T]):
    """Result of a processing operation."""

    success: bool
    data: T | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    processing_time_ms: int = 0

    def __post_init__(self):
        """Validate result data."""
        if self.success and self.data is None:
            raise ValueError("Successful result must have data")
        if not self.success and self.error is None:
            raise ValueError("Failed result must have error message")


class BaseProcessor(ABC, Generic[T, R]):
    """Base class for all data processors."""

    def __init__(self, config: ProcessorConfig):
        """Initialize processor with configuration."""
        self.config = config
        self.logger = logger.bind(processor=config.name)

    @abstractmethod
    async def process(self, input_data: T) -> ProcessingResult[R]:
        """Process input data and return result."""
        pass

    @abstractmethod
    def validate_input(self, input_data: T) -> bool:
        """Validate input data before processing."""
        pass

    async def process_with_retry(self, input_data: T) -> ProcessingResult[R]:
        """Process input data with retry logic."""
        if not self.config.enabled:
            return ProcessingResult(
                success=False,
                error="Processor is disabled",
                metadata={"processor": self.config.name},
            )

        if not self.validate_input(input_data):
            return ProcessingResult(
                success=False,
                error="Input validation failed",
                metadata={"processor": self.config.name},
            )

        for attempt in range(self.config.max_retries + 1):
            try:
                start_time = asyncio.get_event_loop().time()

                # Process with timeout
                result = await asyncio.wait_for(
                    self.process(input_data), timeout=self.config.timeout_seconds
                )

                processing_time_ms = int(
                    (asyncio.get_event_loop().time() - start_time) * 1000
                )
                result.processing_time_ms = processing_time_ms

                self.logger.info(
                    "processing.completed",
                    success=result.success,
                    processing_time_ms=processing_time_ms,
                    attempt=attempt + 1,
                )

                return result

            except asyncio.TimeoutError:
                error_msg = f"Processing timeout after {self.config.timeout_seconds}s"
                self.logger.error("processing.timeout", attempt=attempt + 1)

                if attempt == self.config.max_retries:
                    return ProcessingResult(
                        success=False,
                        error=error_msg,
                        metadata={
                            "processor": self.config.name,
                            "attempts": attempt + 1,
                        },
                    )

            except Exception as e:
                error_msg = f"Processing error: {str(e)}"
                self.logger.error("processing.error", error=str(e), attempt=attempt + 1)

                if attempt == self.config.max_retries:
                    return ProcessingResult(
                        success=False,
                        error=error_msg,
                        metadata={
                            "processor": self.config.name,
                            "attempts": attempt + 1,
                        },
                    )

                # Exponential backoff
                await asyncio.sleep(2**attempt)

        return ProcessingResult(
            success=False,
            error="Max retries exceeded",
            metadata={
                "processor": self.config.name,
                "attempts": self.config.max_retries + 1,
            },
        )
