"""Generic file downloader with support for multiple sources."""

# Audit components
from .audit import (
    DownloadAuditEvent,
    DownloadAuditEventType,
    DownloadAuditQuery,
    DownloadAuditResult,
    DownloadAuditSeverity,
    DownloadAuditStats,
    create_download_audit_event,
    create_suspicious_activity_event,
)
from .audit_hooks import (
    AuditHook,
    CompositeAuditHook,
    DatabaseAuditHook,
    FileAuditHook,
    LoggingAuditHook,
    NoOpAuditHook,
)
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
    # Audit components
    "DownloadAuditEvent",
    "DownloadAuditEventType",
    "DownloadAuditSeverity",
    "DownloadAuditQuery",
    "DownloadAuditResult",
    "DownloadAuditStats",
    "create_download_audit_event",
    "create_suspicious_activity_event",
    "AuditHook",
    "NoOpAuditHook",
    "LoggingAuditHook",
    "FileAuditHook",
    "DatabaseAuditHook",
    "CompositeAuditHook",
]
