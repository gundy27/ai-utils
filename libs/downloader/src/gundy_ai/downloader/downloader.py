"""Universal downloader that handles multiple source types."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog

from .base import BaseDownloader, DownloadResult
from .downloaders import (
    FTPDownloader,
    HTTPDownloader,
    LocalFileDownloader,
    S3Downloader,
    SFTPDownloader,
)
from .file_utils import FileUtils
from .rate_limiter import RateLimiter
from .sources import (
    AnySource,
    FTPSource,
    HTTPSource,
    LocalFileSource,
    S3Source,
    SFTPSource,
)

logger = structlog.get_logger(__name__)


class UniversalDownloader:
    """Universal downloader that can handle multiple source types."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        max_concurrent_downloads: int = 3,
        rate_limit_per_second: float = 1.0,
        destination_directory: str | Path | None = None,
        audit_hook: Any | None = None,  # Will be AuditHook type when imported
    ):
        """Initialize universal downloader.

        Args:
            max_retries: Maximum number of retry attempts
            timeout_seconds: Timeout for download operations
            max_concurrent_downloads: Maximum concurrent downloads
            rate_limit_per_second: Rate limit for downloads per second
            destination_directory: Default destination directory
            audit_hook: Optional audit hook for logging download events
        """
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.audit_hook = audit_hook
        self.destination_directory = (
            Path(destination_directory) if destination_directory else None
        )

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests_per_second=rate_limit_per_second,
            max_concurrent_downloads=max_concurrent_downloads,
        )

        # Initialize individual downloaders with audit hook
        self.downloaders: list[BaseDownloader] = [
            HTTPDownloader(max_retries, timeout_seconds, self.rate_limiter, audit_hook),
            FTPDownloader(max_retries, timeout_seconds, audit_hook),
            SFTPDownloader(max_retries, timeout_seconds, audit_hook),
            S3Downloader(max_retries, timeout_seconds, audit_hook),
            LocalFileDownloader(max_retries, timeout_seconds, audit_hook),
        ]

        self.logger = logger.bind(universal_downloader=True)

        self.logger.info(
            "universal_downloader.initialized",
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            max_concurrent_downloads=max_concurrent_downloads,
            rate_limit_per_second=rate_limit_per_second,
            destination_directory=(
                str(destination_directory) if destination_directory else None
            ),
        )

    async def download(
        self,
        source: AnySource,
        destination: str | Path | None = None,
        filename: str | None = None,
        actor_id: str = "system",
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> DownloadResult:
        """Download from any supported source.

        Args:
            source: Source descriptor
            destination: Destination path (optional if destination_directory is set)
            filename: Custom filename (optional)
            actor_id: ID of the actor performing the download
            tenant_id: Tenant identifier for audit logging
            **kwargs: Additional arguments for specific downloaders

        Returns:
            DownloadResult with success status and file information
        """

        # Determine destination path
        if destination is None:
            if self.destination_directory is None:
                raise ValueError(
                    "Either destination or destination_directory must be provided",
                )
            destination = self.destination_directory

        destination = Path(destination)

        # If destination is a directory, create filename
        if destination.is_dir() or not destination.suffix:
            if filename is None:
                filename = self._generate_filename(source)
            destination = destination / filename

        # Ensure destination directory exists
        await FileUtils.ensure_directory(destination.parent)

        # Get unique filename to avoid conflicts
        destination = await FileUtils.get_unique_filename(
            destination.parent,
            destination.name,
        )

        self.logger.info(
            "download.start",
            source_type=source.source_type.value,
            source_identifier=source.identifier,
            destination=str(destination),
        )

        # Find appropriate downloader
        downloader = self._find_downloader(source)
        if not downloader:
            error_msg = (
                f"No downloader available for source type: {source.source_type.value}"
            )
            self.logger.error(
                "download.no_downloader",
                source_type=source.source_type.value,
            )
            return DownloadResult.error_result(error_msg)

        try:
            # Perform download with retry logic and audit logging
            result = await downloader.download_with_retry(
                source, destination, actor_id=actor_id, tenant_id=tenant_id, **kwargs
            )

            if result.success:
                self.logger.info(
                    "download.success",
                    source_type=source.source_type.value,
                    destination=str(destination),
                    bytes_downloaded=result.bytes_downloaded,
                    download_time=result.download_time_seconds,
                )
            else:
                self.logger.error(
                    "download.failed",
                    source_type=source.source_type.value,
                    destination=str(destination),
                    error=result.error,
                )

            return result

        except Exception as e:
            error_msg = f"Download failed with exception: {str(e)}"
            self.logger.error(
                "download.exception",
                source_type=source.source_type.value,
                error=str(e),
            )
            return DownloadResult.error_result(error_msg)

    async def download_multiple(
        self,
        sources: list[AnySource],
        destination_directory: str | Path | None = None,
        actor_id: str = "system",
        tenant_id: str = "default",
        **kwargs: Any,
    ) -> dict[str, DownloadResult]:
        """Download multiple files concurrently.

        Args:
            sources: List of source descriptors
            destination_directory: Base directory for downloads
            actor_id: ID of the actor performing the downloads
            tenant_id: Tenant identifier for audit logging
            **kwargs: Additional arguments for downloads

        Returns:
            Dictionary mapping source identifiers to download results
        """

        if destination_directory is None:
            destination_directory = self.destination_directory

        if destination_directory is None:
            raise ValueError("destination_directory must be provided")

        destination_directory = Path(destination_directory)
        await FileUtils.ensure_directory(destination_directory)

        self.logger.info(
            "download_multiple.start",
            count=len(sources),
            destination_directory=str(destination_directory),
        )

        # Create download tasks
        tasks = []
        for source in sources:
            filename = self._generate_filename(source)
            destination = destination_directory / filename

            task = self.download(
                source, destination, actor_id=actor_id, tenant_id=tenant_id, **kwargs
            )
            tasks.append((source.identifier, task))

        # Execute downloads concurrently
        results = {}
        completed_tasks = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True,
        )

        for (identifier, _), result in zip(tasks, completed_tasks, strict=False):
            if isinstance(result, Exception):
                results[identifier] = DownloadResult.error_result(
                    f"Task failed: {str(result)}",
                )
            else:
                results[identifier] = result

        # Log summary
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful

        self.logger.info(
            "download_multiple.completed",
            total=len(sources),
            successful=successful,
            failed=failed,
        )

        return results

    def _find_downloader(self, source: AnySource) -> BaseDownloader | None:
        """Find appropriate downloader for the source."""
        for downloader in self.downloaders:
            if downloader.can_handle(source):
                return downloader
        return None

    def _generate_filename(self, source: AnySource) -> str:
        """Generate filename for source."""
        if isinstance(source, HTTPSource):
            # Extract filename from URL
            from urllib.parse import unquote, urlparse

            parsed = urlparse(source.url)
            filename = Path(unquote(parsed.path)).name
            if not filename or "." not in filename:
                filename = f"download_{source.identifier}"
            return filename

        if isinstance(source, FTPSource | SFTPSource):
            # Use remote path filename
            filename = Path(source.remote_path).name
            if not filename:
                filename = f"download_{source.identifier}"
            return filename

        if isinstance(source, S3Source):
            # Use S3 key filename
            filename = Path(source.key).name
            if not filename:
                filename = f"s3_{source.bucket}_{source.identifier}"
            return filename

        if isinstance(source, LocalFileSource):
            # Use source filename
            filename = Path(source.file_path).name
            if not filename:
                filename = f"local_{source.identifier}"
            return filename

        # Default filename
        return f"download_{source.identifier}"

    def add_downloader(self, downloader: BaseDownloader) -> None:
        """Add a custom downloader."""
        self.downloaders.append(downloader)
        self.logger.info(
            "downloader.added",
            downloader_type=downloader.__class__.__name__,
        )

    def set_rate_limit(self, max_requests_per_second: float) -> None:
        """Update rate limiting settings."""
        self.rate_limiter = RateLimiter(
            max_requests_per_second=max_requests_per_second,
            max_concurrent_downloads=self.rate_limiter.max_concurrent_downloads,
        )
        self.logger.info(
            "rate_limit.updated",
            max_requests_per_second=max_requests_per_second,
        )

    def get_stats(self) -> dict[str, Any]:
        """Get downloader statistics."""
        return {
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "destination_directory": (
                str(self.destination_directory) if self.destination_directory else None
            ),
            "available_downloaders": [d.__class__.__name__ for d in self.downloaders],
            "rate_limiter_stats": self.rate_limiter.get_stats(),
        }
