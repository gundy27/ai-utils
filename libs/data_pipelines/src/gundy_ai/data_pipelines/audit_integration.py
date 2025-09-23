"""Audit integration for data pipelines processing."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

import structlog

logger = structlog.get_logger(__name__)


class ProcessingAuditEvent:
    """Audit event for document processing operations."""

    def __init__(
        self,
        event_id: str | None = None,
        event_type: str = "document_processing",
        timestamp: datetime | None = None,
        actor_id: str = "system",
        tenant_id: str = "default",
        session_id: str | None = None,
        # Processing details
        file_path: str = "",
        file_name: str = "",
        file_size: int = 0,
        document_type: str = "",
        # Processing results
        success: bool = True,
        error_message: str | None = None,
        processing_time_ms: float = 0.0,
        # Content metrics
        text_length: int = 0,
        word_count: int = 0,
        chunk_count: int = 0,
        # Processing metadata
        parser_used: str | None = None,
        chunking_strategy: str | None = None,
        text_cleaning_enabled: bool = False,
        ocr_used: bool = False,
        # Additional context
        metadata: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ):
        """Initialize processing audit event."""
        self.event_id = event_id or str(uuid4())
        self.event_type = event_type
        self.timestamp = timestamp or datetime.utcnow()
        self.actor_id = actor_id
        self.tenant_id = tenant_id
        self.session_id = session_id

        self.file_path = file_path
        self.file_name = file_name
        self.file_size = file_size
        self.document_type = document_type

        self.success = success
        self.error_message = error_message
        self.processing_time_ms = processing_time_ms

        self.text_length = text_length
        self.word_count = word_count
        self.chunk_count = chunk_count

        self.parser_used = parser_used
        self.chunking_strategy = chunking_strategy
        self.text_cleaning_enabled = text_cleaning_enabled
        self.ocr_used = ocr_used

        self.metadata = metadata or {}
        self.tags = tags or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/storage."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "document_type": self.document_type,
            "success": self.success,
            "error_message": self.error_message,
            "processing_time_ms": self.processing_time_ms,
            "text_length": self.text_length,
            "word_count": self.word_count,
            "chunk_count": self.chunk_count,
            "parser_used": self.parser_used,
            "chunking_strategy": self.chunking_strategy,
            "text_cleaning_enabled": self.text_cleaning_enabled,
            "ocr_used": self.ocr_used,
            "metadata": self.metadata,
            "tags": self.tags,
        }


class ProcessingAuditHook:
    """Audit hook interface for data pipelines processing."""

    def __init__(self, audit_hook: Any | None = None):
        """Initialize with optional audit hook from downloader module."""
        self.audit_hook = audit_hook
        self.logger = logger.bind(component="processing_audit")

    async def log_processing_start(
        self,
        file_path: str,
        actor_id: str = "system",
        tenant_id: str = "default",
        session_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Log the start of document processing."""
        from pathlib import Path

        path = Path(file_path)
        event_id = str(uuid4())

        event = ProcessingAuditEvent(
            event_id=event_id,
            event_type="processing_start",
            actor_id=actor_id,
            tenant_id=tenant_id,
            session_id=session_id,
            file_path=str(path),
            file_name=path.name,
            file_size=path.stat().st_size if path.exists() else 0,
            document_type=path.suffix.lower(),
            tags=["processing", "start"],
            metadata=kwargs,
        )

        await self._log_event(event)
        return event_id

    async def log_processing_success(
        self,
        event_id: str,
        processing_time_ms: float,
        text_length: int = 0,
        word_count: int = 0,
        chunk_count: int = 0,
        parser_used: str | None = None,
        chunking_strategy: str | None = None,
        text_cleaning_enabled: bool = False,
        ocr_used: bool = False,
        **kwargs: Any,
    ) -> None:
        """Log successful processing completion."""
        event = ProcessingAuditEvent(
            event_id=event_id,
            event_type="processing_success",
            success=True,
            processing_time_ms=processing_time_ms,
            text_length=text_length,
            word_count=word_count,
            chunk_count=chunk_count,
            parser_used=parser_used,
            chunking_strategy=chunking_strategy,
            text_cleaning_enabled=text_cleaning_enabled,
            ocr_used=ocr_used,
            tags=["processing", "success"],
            metadata=kwargs,
        )

        await self._log_event(event)

    async def log_processing_failure(
        self,
        event_id: str,
        error_message: str,
        processing_time_ms: float,
        **kwargs: Any,
    ) -> None:
        """Log processing failure."""
        event = ProcessingAuditEvent(
            event_id=event_id,
            event_type="processing_failure",
            success=False,
            error_message=error_message,
            processing_time_ms=processing_time_ms,
            tags=["processing", "failure", "error"],
            metadata=kwargs,
        )

        await self._log_event(event)

    async def log_parsing_attempt(
        self,
        event_id: str,
        parser_name: str,
        success: bool,
        processing_time_ms: float,
        text_length: int = 0,
        error_message: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Log individual parser attempt."""
        event = ProcessingAuditEvent(
            event_id=str(uuid4()),
            event_type="parsing_attempt",
            success=success,
            processing_time_ms=processing_time_ms,
            text_length=text_length,
            parser_used=parser_name,
            error_message=error_message,
            tags=["parsing", parser_name, "success" if success else "failure"],
            metadata={"parent_event_id": event_id, **kwargs},
        )

        await self._log_event(event)

    async def log_text_cleaning(
        self,
        event_id: str,
        cleaning_strategy: str,
        original_length: int,
        cleaned_length: int,
        processing_time_ms: float,
        cleaning_steps: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        """Log text cleaning operation."""
        event = ProcessingAuditEvent(
            event_id=str(uuid4()),
            event_type="text_cleaning",
            success=True,
            processing_time_ms=processing_time_ms,
            text_length=cleaned_length,
            text_cleaning_enabled=True,
            tags=["text_cleaning", cleaning_strategy],
            metadata={
                "parent_event_id": event_id,
                "cleaning_strategy": cleaning_strategy,
                "original_length": original_length,
                "cleaned_length": cleaned_length,
                "reduction_ratio": (
                    (original_length - cleaned_length) / original_length
                    if original_length > 0
                    else 0
                ),
                "cleaning_steps": cleaning_steps or [],
                **kwargs,
            },
        )

        await self._log_event(event)

    async def log_chunking_operation(
        self,
        event_id: str,
        chunking_strategy: str,
        chunk_count: int,
        processing_time_ms: float,
        avg_chunk_size: float = 0.0,
        **kwargs: Any,
    ) -> None:
        """Log text chunking operation."""
        event = ProcessingAuditEvent(
            event_id=str(uuid4()),
            event_type="text_chunking",
            success=True,
            processing_time_ms=processing_time_ms,
            chunk_count=chunk_count,
            chunking_strategy=chunking_strategy,
            tags=["chunking", chunking_strategy],
            metadata={
                "parent_event_id": event_id,
                "avg_chunk_size": avg_chunk_size,
                **kwargs,
            },
        )

        await self._log_event(event)

    async def _log_event(self, event: ProcessingAuditEvent) -> None:
        """Log event using available audit hook or fallback to structured logging."""
        try:
            if self.audit_hook and hasattr(self.audit_hook, "log_download_event"):
                # Try to adapt to downloader audit hook interface
                # This would need to be customized based on the actual interface
                await self._log_to_downloader_audit_hook(event)
            else:
                # Fallback to structured logging
                self.logger.info("processing_audit_event", **event.to_dict())
        except Exception as e:
            self.logger.error(
                "audit_logging_error", error=str(e), event_id=event.event_id
            )

    async def _log_to_downloader_audit_hook(self, event: ProcessingAuditEvent) -> None:
        """Adapt processing event to downloader audit hook format."""
        # This would create a compatible audit event for the downloader system
        # For now, we'll use structured logging as the primary mechanism
        self.logger.info(
            "processing_audit_event_via_downloader_hook", **event.to_dict()
        )
