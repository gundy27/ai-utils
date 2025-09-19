"""Individual downloader implementations."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import aiohttp
import structlog

from .base import BaseDownloader, DownloadResult, LocalFile
from .file_utils import FileUtils
from .rate_limiter import RateLimiter
from .sources import (
    FTPSource,
    HTTPSource,
    LocalFileSource,
    S3Source,
    SFTPSource,
)

logger = structlog.get_logger(__name__)


class HTTPDownloader(BaseDownloader):
    """HTTP/HTTPS downloader."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        rate_limiter: RateLimiter | None = None,
        audit_hook: Any | None = None,
    ):
        """Initialize HTTP downloader."""
        super().__init__(max_retries, timeout_seconds, audit_hook)
        self.rate_limiter = rate_limiter
        self.logger = logger.bind(downloader="http")

    def can_handle(self, source: Any) -> bool:
        """Check if this downloader can handle the source."""
        return isinstance(source, HTTPSource)

    async def download(
        self,
        source: HTTPSource,
        destination: str | Path,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download from HTTP/HTTPS source."""

        destination = Path(destination)
        start_time = time.time()

        try:
            # Apply rate limiting
            if self.rate_limiter:
                domain = urlparse(source.url).netloc
                async with self.rate_limiter:
                    await self.rate_limiter.acquire(domain)

            # Prepare request parameters
            connector = aiohttp.TCPConnector(ssl=source.verify_ssl)
            timeout = aiohttp.ClientTimeout(total=source.timeout)

            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=source.headers,
            ) as session:
                # Prepare authentication
                auth = None
                if source.auth:
                    auth = aiohttp.BasicAuth(
                        source.auth.get("username", ""),
                        source.auth.get("password", ""),
                    )

                # Make request
                async with session.request(
                    method=source.method,
                    url=source.url,
                    params=source.params,
                    cookies=source.cookies,
                    auth=auth,
                    allow_redirects=source.follow_redirects,
                    max_redirects=source.max_redirects,
                ) as response:
                    if response.status >= 400:
                        error_msg = f"HTTP {response.status}: {response.reason}"
                        return DownloadResult.error_result(error_msg)

                    # Ensure destination directory exists
                    await FileUtils.ensure_directory(destination.parent)

                    # Download content
                    content = await response.read()
                    bytes_downloaded = len(content)

                    # Write file
                    local_file = await FileUtils.write_file_async(
                        destination,
                        content,
                        "wb",
                    )

                    download_time = time.time() - start_time

                    return DownloadResult.success_result(
                        local_file=local_file,
                        bytes_downloaded=bytes_downloaded,
                        download_time_seconds=download_time,
                        metadata={
                            "status_code": response.status,
                            "headers": dict(response.headers),
                            "url": source.url,
                        },
                    )

        except TimeoutError:
            return DownloadResult.error_result(
                f"Download timeout after {source.timeout} seconds",
            )
        except Exception as e:
            return DownloadResult.error_result(f"Download failed: {str(e)}")


class FTPDownloader(BaseDownloader):
    """FTP downloader."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        audit_hook: Any | None = None,
    ):
        """Initialize FTP downloader."""
        super().__init__(max_retries, timeout_seconds, audit_hook)
        self.logger = logger.bind(downloader="ftp")

    def can_handle(self, source: Any) -> bool:
        """Check if this downloader can handle the source."""
        return isinstance(source, FTPSource)

    async def download(
        self,
        source: FTPSource,
        destination: str | Path,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download from FTP source."""

        destination = Path(destination)
        start_time = time.time()

        try:
            import ftplib

            # Connect to FTP server
            ftp = ftplib.FTP()
            ftp.connect(source.host, source.port, source.timeout)
            ftp.login(source.username, source.password)

            if source.passive_mode:
                ftp.set_pasv(True)

            # Set transfer mode
            if source.binary_mode:
                ftp.voidcmd("TYPE I")
            else:
                ftp.voidcmd("TYPE A")

            # Get file size
            try:
                file_size = ftp.size(source.remote_path)
            except Exception:
                file_size = None

            # Download file
            bytes_downloaded = 0
            content = bytearray()

            def callback(data):
                nonlocal bytes_downloaded
                content.extend(data)
                bytes_downloaded += len(data)

            ftp.retrbinary(f"RETR {source.remote_path}", callback)
            ftp.quit()

            # Write file
            await FileUtils.ensure_directory(destination.parent)
            local_file = await FileUtils.write_file_async(destination, bytes(content))

            download_time = time.time() - start_time

            return DownloadResult.success_result(
                local_file=local_file,
                bytes_downloaded=bytes_downloaded,
                download_time_seconds=download_time,
                metadata={
                    "ftp_host": source.host,
                    "remote_path": source.remote_path,
                    "file_size": file_size,
                },
            )

        except Exception as e:
            return DownloadResult.error_result(f"FTP download failed: {str(e)}")


class SFTPDownloader(BaseDownloader):
    """SFTP downloader."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        audit_hook: Any | None = None,
    ):
        """Initialize SFTP downloader."""
        super().__init__(max_retries, timeout_seconds, audit_hook)
        self.logger = logger.bind(downloader="sftp")

    def can_handle(self, source: Any) -> bool:
        """Check if this downloader can handle the source."""
        return isinstance(source, SFTPSource)

    async def download(
        self,
        source: SFTPSource,
        destination: str | Path,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download from SFTP source."""

        destination = Path(destination)
        start_time = time.time()

        try:
            import paramiko

            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Prepare authentication
            auth_kwargs = {
                "hostname": source.host,
                "port": source.port,
                "username": source.username,
                "timeout": source.timeout,
            }

            if source.password:
                auth_kwargs["password"] = source.password
            elif source.private_key_path:
                auth_kwargs["key_filename"] = source.private_key_path
                if source.private_key_passphrase:
                    auth_kwargs["passphrase"] = source.private_key_passphrase

            # Connect
            ssh.connect(**auth_kwargs)

            # Create SFTP client
            sftp = ssh.open_sftp()

            # Get file attributes
            file_attrs = sftp.stat(source.remote_path)
            file_size = file_attrs.st_size

            # Download file
            bytes_downloaded = 0
            content = bytearray()

            def callback(data):
                nonlocal bytes_downloaded
                content.extend(data)
                bytes_downloaded += len(data)

            sftp.get(source.remote_path, str(destination), callback=callback)

            # Close connections
            sftp.close()
            ssh.close()

            # Compute checksum and create LocalFile
            from .base import FileChecksum

            checksum = FileChecksum.compute_file_hash(destination)
            local_file = LocalFile(
                path=destination,
                checksum=checksum,
                metadata={
                    "sftp_host": source.host,
                    "remote_path": source.remote_path,
                    "file_size": file_size,
                },
            )

            download_time = time.time() - start_time

            return DownloadResult.success_result(
                local_file=local_file,
                bytes_downloaded=bytes_downloaded,
                download_time_seconds=download_time,
                metadata={
                    "sftp_host": source.host,
                    "remote_path": source.remote_path,
                    "file_size": file_size,
                },
            )

        except Exception as e:
            return DownloadResult.error_result(f"SFTP download failed: {str(e)}")


class S3Downloader(BaseDownloader):
    """AWS S3 downloader."""

    def __init__(
        self,
        max_retries: int = 3,
        timeout_seconds: int = 300,
        audit_hook: Any | None = None,
    ):
        """Initialize S3 downloader."""
        super().__init__(max_retries, timeout_seconds, audit_hook)
        self.logger = logger.bind(downloader="s3")

    def can_handle(self, source: Any) -> bool:
        """Check if this downloader can handle the source."""
        return isinstance(source, S3Source)

    async def download(
        self,
        source: S3Source,
        destination: str | Path,
        **kwargs: Any,
    ) -> DownloadResult:
        """Download from S3 source."""

        destination = Path(destination)
        start_time = time.time()

        try:
            import boto3
            from botocore.exceptions import ClientError

            # Create S3 client
            s3_kwargs = {"region_name": source.region, "use_ssl": source.use_ssl}

            if source.access_key_id and source.secret_access_key:
                s3_kwargs.update(
                    {
                        "aws_access_key_id": source.access_key_id,
                        "aws_secret_access_key": source.secret_access_key,
                    },
                )

            if source.session_token:
                s3_kwargs["aws_session_token"] = source.session_token

            if source.endpoint_url:
                s3_kwargs["endpoint_url"] = source.endpoint_url

            s3_client = boto3.client("s3", **s3_kwargs)

            # Download object
            download_kwargs = {"Bucket": source.bucket, "Key": source.key}

            if source.version_id:
                download_kwargs["VersionId"] = source.version_id

            response = s3_client.get_object(**download_kwargs)

            # Read content
            content = response["Body"].read()
            bytes_downloaded = len(content)

            # Write file
            await FileUtils.ensure_directory(destination.parent)
            local_file = await FileUtils.write_file_async(destination, content)

            download_time = time.time() - start_time

            return DownloadResult.success_result(
                local_file=local_file,
                bytes_downloaded=bytes_downloaded,
                download_time_seconds=download_time,
                metadata={
                    "bucket": source.bucket,
                    "key": source.key,
                    "version_id": source.version_id,
                    "content_length": response.get("ContentLength"),
                    "etag": response.get("ETag"),
                },
            )

        except ClientError as e:
            return DownloadResult.error_result(f"S3 download failed: {str(e)}")
        except Exception as e:
            return DownloadResult.error_result(f"S3 download failed: {str(e)}")


class LocalFileDownloader(BaseDownloader):
    """Local file downloader (copy/move operations)."""

    def __init__(
        self,
        max_retries: int = 1,
        timeout_seconds: int = 60,
        audit_hook: Any | None = None,
    ):
        """Initialize local file downloader."""
        super().__init__(max_retries, timeout_seconds, audit_hook)
        self.logger = logger.bind(downloader="local_file")

    def can_handle(self, source: Any) -> bool:
        """Check if this downloader can handle the source."""
        return isinstance(source, LocalFileSource)

    async def download(
        self,
        source: LocalFileSource,
        destination: str | Path,
        **kwargs: Any,
    ) -> DownloadResult:
        """Copy/move local file."""

        destination = Path(destination)
        start_time = time.time()

        try:
            source_path = Path(source.file_path)

            if not source_path.exists():
                return DownloadResult.error_result(
                    f"Source file not found: {source_path}",
                )

            # Ensure destination directory exists
            await FileUtils.ensure_directory(destination.parent)

            # Copy or move file
            if source.move_file:
                local_file = await FileUtils.move_file(
                    source_path,
                    destination,
                    preserve_metadata=source.preserve_metadata,
                )
                operation = "move"
            else:
                local_file = await FileUtils.copy_file(
                    source_path,
                    destination,
                    preserve_metadata=source.preserve_metadata,
                )
                operation = "copy"

            bytes_downloaded = local_file.size()
            download_time = time.time() - start_time

            return DownloadResult.success_result(
                local_file=local_file,
                bytes_downloaded=bytes_downloaded,
                download_time_seconds=download_time,
                metadata={
                    "operation": operation,
                    "source_path": str(source_path),
                    "preserve_metadata": source.preserve_metadata,
                },
            )

        except Exception as e:
            return DownloadResult.error_result(f"Local file operation failed: {str(e)}")


# LocalFile import moved to top of file to avoid E402
