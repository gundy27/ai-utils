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

    def __init__(self, max_retries: int = 3, timeout_seconds: int = 300):
        """Initialize base downloader."""
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
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

    async def download_with_retry(
        self,
        source: Any,
        destination: str | Path,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download with retry logic."""
        destination = Path(destination)

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
                    return result
                self.logger.warning(
                    "download.failed",
                    attempt=attempt + 1,
                    error=result.error,
                )

                if attempt == self.max_retries:
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
                    return DownloadResult.error_result(
                        f"Download failed after {self.max_retries + 1} attempts: {str(e)}",
                    )

                await asyncio.sleep(2**attempt)

        return DownloadResult.error_result("Download failed after all retries")
