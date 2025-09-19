"""Base classes and models for the downloader module."""

from __future__ import annotations

import asyncio
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class SourceType(Enum):
    """Types of download sources."""

    HTTP = "http"
    HTTPS = "https"
    FTP = "ftp"
    SFTP = "sftp"
    S3 = "s3"
    LOCAL_FILE = "local_file"
    VENDOR_PORTAL = "vendor_portal"


class DownloadStatus(Enum):
    """Download status enumeration."""

    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DownloadError(Exception):
    """Custom exception for download errors."""

    message: str
    source: str
    status_code: int | None = None
    error_type: str | None = None

    def __str__(self) -> str:
        return f"DownloadError: {self.message} (source: {self.source})"


class FileChecksum(BaseModel):
    """File checksum information."""

    algorithm: str = Field(default="sha256", description="Hash algorithm used")
    value: str = Field(description="Hash value")
    size_bytes: int = Field(description="File size in bytes")

    def verify(self, file_path: str | Path) -> bool:
        """Verify the checksum of a file."""
        file_path = Path(file_path)
        if not file_path.exists():
            return False

        if file_path.stat().st_size != self.size_bytes:
            return False

        computed_hash = self._compute_hash(file_path)
        return computed_hash == self.value

    def _compute_hash(self, file_path: Path) -> str:
        """Compute hash of file."""
        hash_func = hashlib.new(self.algorithm)

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()

    @classmethod
    def compute_file_hash(
        cls,
        file_path: str | Path,
        algorithm: str = "sha256",
    ) -> FileChecksum:
        """Compute hash for a file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        size_bytes = file_path.stat().st_size
        hash_value = cls._compute_hash_static(file_path, algorithm)

        return cls(algorithm=algorithm, value=hash_value, size_bytes=size_bytes)

    @staticmethod
    def _compute_hash_static(file_path: Path, algorithm: str) -> str:
        """Static method to compute hash."""
        hash_func = hashlib.new(algorithm)

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_func.update(chunk)

        return hash_func.hexdigest()


class LocalFile(BaseModel):
    """Local file information."""

    path: Path = Field(description="Path to the local file")
    checksum: FileChecksum = Field(description="File checksum information")
    downloaded_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        """Initialize LocalFile with path conversion."""
        if "path" in data and isinstance(data["path"], str):
            data["path"] = Path(data["path"])
        super().__init__(**data)

    def exists(self) -> bool:
        """Check if the file exists."""
        return self.path.exists()

    def size(self) -> int:
        """Get file size in bytes."""
        if not self.exists():
            return 0
        return self.path.stat().st_size

    def verify_checksum(self) -> bool:
        """Verify the file checksum."""
        return self.checksum.verify(self.path)

    def delete(self) -> bool:
        """Delete the local file."""
        try:
            if self.exists():
                self.path.unlink()
                return True
            return False
        except Exception as e:
            logger.error("file.delete.error", path=str(self.path), error=str(e))
            return False


class DownloadResult(BaseModel):
    """Result of a download operation."""

    success: bool = Field(description="Whether download was successful")
    local_file: LocalFile | None = Field(
        None,
        description="Downloaded file information",
    )
    error: str | None = Field(None, description="Error message if failed")
    status: DownloadStatus = Field(description="Download status")
    bytes_downloaded: int = Field(default=0, description="Number of bytes downloaded")
    download_time_seconds: float = Field(
        default=0.0,
        description="Time taken to download",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def success_result(
        cls,
        local_file: LocalFile,
        bytes_downloaded: int,
        download_time_seconds: float,
        metadata: dict[str, Any] | None = None,
    ) -> DownloadResult:
        """Create a successful download result."""
        return cls(
            success=True,
            local_file=local_file,
            status=DownloadStatus.COMPLETED,
            bytes_downloaded=bytes_downloaded,
            download_time_seconds=download_time_seconds,
            metadata=metadata or {},
        )

    @classmethod
    def error_result(
        cls,
        error: str,
        metadata: dict[str, Any] | None = None,
    ) -> DownloadResult:
        """Create a failed download result."""
        return cls(
            success=False,
            error=error,
            status=DownloadStatus.FAILED,
            metadata=metadata or {},
        )

    @classmethod
    def skipped_result(
        cls,
        reason: str,
        metadata: dict[str, Any] | None = None,
    ) -> DownloadResult:
        """Create a skipped download result."""
        return cls(
            success=True,
            status=DownloadStatus.SKIPPED,
            metadata={"skip_reason": reason, **(metadata or {})},
        )


class BaseDownloader(ABC):
    """Base class for all downloaders."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        audit_hook: Any | None = None,  # Will be AuditHook type when imported
    ):
        """Initialize base downloader.

        Args:
            max_retries: Maximum number of retry attempts
            timeout_seconds: Timeout for download operations
            audit_hook: Optional audit hook for logging download events
        """
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.audit_hook = audit_hook
        self.logger = logger.bind(downloader=self.__class__.__name__)

    @abstractmethod
    async def download(
        self,
        source: Any,  # SourceDescriptor will be defined later
        destination: str | Path,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download from source to destination."""

    @abstractmethod
    def can_handle(self, source: Any) -> bool:
        """Check if this downloader can handle the given source."""

    async def _log_audit_event(
        self,
        event_type: str,
        actor_id: str,
        tenant_id: str,
        source: Any,
        destination: str | Path,
        success: bool,
        **kwargs: Any,
    ) -> None:
        """Log an audit event if audit hook is configured.

        Args:
            event_type: Type of audit event
            actor_id: ID of the actor performing the action
            tenant_id: Tenant identifier
            source: Download source
            destination: Destination path
            success: Whether the operation was successful
            **kwargs: Additional fields for the audit event
        """
        if not self.audit_hook:
            return

        try:
            # Import here to avoid circular imports
            from .audit import (
                DownloadAuditEventType,
                DownloadAuditSeverity,
                create_download_audit_event,
            )

            # Map string event types to enum values
            event_type_map = {
                "download_start": DownloadAuditEventType.DOWNLOAD_START,
                "download_success": DownloadAuditEventType.DOWNLOAD_SUCCESS,
                "download_failure": DownloadAuditEventType.DOWNLOAD_FAILURE,
                "download_retry": DownloadAuditEventType.DOWNLOAD_RETRY,
                "file_integrity_verification": DownloadAuditEventType.FILE_INTEGRITY_VERIFICATION,
                "file_integrity_failure": DownloadAuditEventType.FILE_INTEGRITY_FAILURE,
            }

            audit_event_type = event_type_map.get(
                event_type, DownloadAuditEventType.DOWNLOAD_START
            )

            # Determine severity based on success and event type
            severity = (
                DownloadAuditSeverity.ERROR
                if not success
                else DownloadAuditSeverity.INFO
            )
            if event_type in ["file_integrity_failure", "suspicious_activity"]:
                severity = DownloadAuditSeverity.WARNING

            # Extract source information
            source_identifier = getattr(source, "identifier", "unknown")
            source_type = getattr(source, "source_type", None)
            source_uri = getattr(source, "get_uri", lambda: "")()

            # Create audit event
            audit_event = create_download_audit_event(
                event_type=audit_event_type,
                actor_id=actor_id,
                tenant_id=tenant_id,
                source_identifier=source_identifier,
                source_type=source_type,
                source_uri=source_uri,
                destination_path=str(destination),
                success=success,
                severity=severity,
                **kwargs,
            )

            # Log the event
            await self.audit_hook.log_download_event(audit_event)

        except Exception as e:
            # Don't let audit logging failures break downloads
            self.logger.warning(
                "audit_logging_failed",
                error=str(e),
                event_type=event_type,
                source_identifier=getattr(source, "identifier", "unknown"),
            )

    async def download_with_retry(
        self,
        source: Any,
        destination: str | Path,
        actor_id: str = "system",
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> DownloadResult:
        """Download with retry logic and audit logging."""
        destination = Path(destination)
        start_time = datetime.utcnow()

        # Log download start
        await self._log_audit_event(
            event_type="download_start",
            actor_id=actor_id,
            tenant_id=tenant_id,
            source=source,
            destination=destination,
            success=True,
            retry_count=0,
        )

        for attempt in range(self.max_retries + 1):
            try:
                self.logger.debug(
                    "download.attempt",
                    attempt=attempt + 1,
                    max_retries=self.max_retries,
                    destination=str(destination),
                )

                result = await self.download(source, destination, **kwargs)

                if result.success:
                    self.logger.info(
                        "download.success",
                        attempt=attempt + 1,
                        destination=str(destination),
                        bytes_downloaded=result.bytes_downloaded,
                        download_time=result.download_time_seconds,
                    )

                    # Log successful download
                    await self._log_audit_event(
                        event_type="download_success",
                        actor_id=actor_id,
                        tenant_id=tenant_id,
                        source=source,
                        destination=destination,
                        success=True,
                        retry_count=attempt,
                        file_name=(
                            result.local_file.path.name if result.local_file else None
                        ),
                        file_size=result.bytes_downloaded,
                        file_checksum=(
                            result.local_file.checksum.value
                            if result.local_file
                            else None
                        ),
                        download_duration_ms=result.download_time_seconds * 1000,
                        bytes_downloaded=result.bytes_downloaded,
                    )
                    return result

                self.logger.warning(
                    "download.failed",
                    attempt=attempt + 1,
                    error=result.error,
                )

                # Log retry attempt
                if attempt < self.max_retries:
                    await self._log_audit_event(
                        event_type="download_retry",
                        actor_id=actor_id,
                        tenant_id=tenant_id,
                        source=source,
                        destination=destination,
                        success=False,
                        retry_count=attempt + 1,
                        error_message=result.error,
                    )

                if attempt == self.max_retries:
                    # Log final failure
                    await self._log_audit_event(
                        event_type="download_failure",
                        actor_id=actor_id,
                        tenant_id=tenant_id,
                        source=source,
                        destination=destination,
                        success=False,
                        retry_count=attempt,
                        error_message=result.error,
                        download_duration_ms=(
                            datetime.utcnow() - start_time
                        ).total_seconds()
                        * 1000,
                    )
                    return result

                # Wait before retry (exponential backoff)
                await asyncio.sleep(2**attempt)

            except Exception as e:
                self.logger.error(
                    "download.exception",
                    attempt=attempt + 1,
                    error=str(e),
                )

                if attempt == self.max_retries:
                    error_result = DownloadResult.error_result(
                        f"Download failed after {self.max_retries + 1} attempts: {str(e)}",
                    )

                    # Log final failure with exception
                    await self._log_audit_event(
                        event_type="download_failure",
                        actor_id=actor_id,
                        tenant_id=tenant_id,
                        source=source,
                        destination=destination,
                        success=False,
                        retry_count=attempt,
                        error_message=str(e),
                        error_code="EXCEPTION",
                        download_duration_ms=(
                            datetime.utcnow() - start_time
                        ).total_seconds()
                        * 1000,
                    )
                    return error_result

                # Log retry attempt with exception
                await self._log_audit_event(
                    event_type="download_retry",
                    actor_id=actor_id,
                    tenant_id=tenant_id,
                    source=source,
                    destination=destination,
                    success=False,
                    retry_count=attempt + 1,
                    error_message=str(e),
                    error_code="EXCEPTION",
                )

                await asyncio.sleep(2**attempt)

        # This should never be reached, but just in case
        final_error = DownloadResult.error_result("Download failed after all retries")
        await self._log_audit_event(
            event_type="download_failure",
            actor_id=actor_id,
            tenant_id=tenant_id,
            source=source,
            destination=destination,
            success=False,
            retry_count=self.max_retries,
            error_message="Download failed after all retries",
            download_duration_ms=(datetime.utcnow() - start_time).total_seconds()
            * 1000,
        )
        return final_error
