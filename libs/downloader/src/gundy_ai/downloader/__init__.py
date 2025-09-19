"""Generic file downloader with support for multiple sources."""

from .base import BaseDownloader, DownloadResult, DownloadError
from .sources import (
    SourceDescriptor,
    HTTPSource,
    FTPSource,
    SFTPSource,
    S3Source,
    LocalFileSource,
)
from .downloader import UniversalDownloader
from .rate_limiter import RateLimiter
from .file_utils import LocalFile, FileChecksum

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
