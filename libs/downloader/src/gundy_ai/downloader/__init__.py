"""Generic file downloader with support for multiple sources."""

from .base import BaseDownloader, DownloadError, DownloadResult
from .downloader import UniversalDownloader
from .file_utils import FileChecksum, LocalFile
from .rate_limiter import RateLimiter
from .sources import (
    FTPSource,
    HTTPSource,
    LocalFileSource,
    S3Source,
    SFTPSource,
    SourceDescriptor,
)

__version__ = "0.1.0"
__all__ = [
    # Core classes
    "BaseDownloader",
    "DownloadResult",
    "DownloadError",
    "UniversalDownloader",
    "RateLimiter",
    "LocalFile",
    "FileChecksum",
    # Source types
    "SourceDescriptor",
    "HTTPSource",
    "FTPSource",
    "SFTPSource",
    "S3Source",
    "LocalFileSource",
]
