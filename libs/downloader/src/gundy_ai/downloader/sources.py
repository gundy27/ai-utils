"""Source descriptor models for different download sources."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, validator

from .base import SourceType


class SourceDescriptor(BaseModel):
    """Base class for source descriptors."""

    source_type: SourceType = Field(description="Type of source")
    identifier: str = Field(description="Unique identifier for the source")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class HTTPSource(SourceDescriptor):
    """HTTP/HTTPS source descriptor."""

    source_type: SourceType = Field(default=SourceType.HTTP, description="Source type")
    url: str = Field(description="URL to download from")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers")
    auth: dict[str, str] | None = Field(None, description="Authentication credentials")
    method: str = Field(default="GET", description="HTTP method")
    params: dict[str, Any] = Field(default_factory=dict, description="Query parameters")
    cookies: dict[str, str] = Field(default_factory=dict, description="Cookies")
    follow_redirects: bool = Field(
        default=True,
        description="Whether to follow redirects",
    )
    max_redirects: int = Field(default=10, description="Maximum number of redirects")
    verify_ssl: bool = Field(
        default=True,
        description="Whether to verify SSL certificates",
    )
    timeout: int = Field(default=300, description="Timeout in seconds")

    @validator("url")
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @validator("method")
    def validate_method(cls, v):
        """Validate HTTP method."""
        allowed_methods = {"GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"}
        if v.upper() not in allowed_methods:
            raise ValueError(f"HTTP method must be one of: {allowed_methods}")
        return v.upper()


class FTPSource(SourceDescriptor):
    """FTP source descriptor."""

    source_type: SourceType = Field(default=SourceType.FTP, description="Source type")
    host: str = Field(description="FTP server hostname")
    port: int = Field(default=21, description="FTP server port")
    username: str = Field(description="FTP username")
    password: str = Field(description="FTP password")
    remote_path: str = Field(description="Remote file path")
    passive_mode: bool = Field(default=True, description="Use passive mode")
    binary_mode: bool = Field(default=True, description="Use binary transfer mode")
    timeout: int = Field(default=300, description="Connection timeout in seconds")


class SFTPSource(SourceDescriptor):
    """SFTP source descriptor."""

    source_type: SourceType = Field(default=SourceType.SFTP, description="Source type")
    host: str = Field(description="SFTP server hostname")
    port: int = Field(default=22, description="SFTP server port")
    username: str = Field(description="SFTP username")
    password: str | None = Field(None, description="SFTP password")
    private_key_path: str | None = Field(None, description="Path to private key file")
    private_key_passphrase: str | None = Field(
        None,
        description="Private key passphrase",
    )
    remote_path: str = Field(description="Remote file path")
    timeout: int = Field(default=300, description="Connection timeout in seconds")

    @validator("password", "private_key_path")
    def validate_auth(cls, v, values):
        """Validate that either password or private key is provided."""
        if not v and not values.get("private_key_path") and not values.get("password"):
            raise ValueError("Either password or private_key_path must be provided")
        return v


class S3Source(SourceDescriptor):
    """AWS S3 source descriptor."""

    source_type: SourceType = Field(default=SourceType.S3, description="Source type")
    bucket: str = Field(description="S3 bucket name")
    key: str = Field(description="S3 object key")
    region: str | None = Field(None, description="AWS region")
    access_key_id: str | None = Field(None, description="AWS access key ID")
    secret_access_key: str | None = Field(None, description="AWS secret access key")
    session_token: str | None = Field(None, description="AWS session token")
    version_id: str | None = Field(None, description="S3 object version ID")
    endpoint_url: str | None = Field(None, description="Custom S3 endpoint URL")
    use_ssl: bool = Field(default=True, description="Use SSL for S3 connection")
    signature_version: str = Field(default="s3v4", description="S3 signature version")

    @validator("region")
    def validate_region(cls, v):
        """Validate AWS region format."""
        if v and not v.replace("-", "").isalnum():
            raise ValueError("Invalid AWS region format")
        return v


class LocalFileSource(SourceDescriptor):
    """Local file source descriptor (for copying/moving files)."""

    source_type: SourceType = Field(
        default=SourceType.LOCAL_FILE,
        description="Source type",
    )
    file_path: str = Field(description="Path to the local file")
    move_file: bool = Field(
        default=False,
        description="Whether to move instead of copy",
    )
    preserve_metadata: bool = Field(default=True, description="Preserve file metadata")

    @validator("file_path")
    def validate_file_path(cls, v):
        """Validate that file path exists."""
        from pathlib import Path

        path = Path(v)
        if not path.exists():
            raise ValueError(f"File does not exist: {v}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {v}")
        return v


class VendorPortalSource(SourceDescriptor):
    """Vendor portal source descriptor (generic)."""

    source_type: SourceType = Field(
        default=SourceType.VENDOR_PORTAL,
        description="Source type",
    )
    portal_url: str = Field(description="Portal base URL")
    login_url: str = Field(description="Login endpoint URL")
    download_url: str = Field(description="Download endpoint URL")
    username: str = Field(description="Portal username")
    password: str = Field(description="Portal password")
    resource_id: str = Field(description="Resource identifier")
    session_cookies: dict[str, str] = Field(
        default_factory=dict,
        description="Session cookies",
    )
    additional_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional headers",
    )
    authentication_method: str = Field(
        default="form",
        description="Authentication method",
    )
    timeout: int = Field(default=300, description="Request timeout in seconds")

    @validator("authentication_method")
    def validate_auth_method(cls, v):
        """Validate authentication method."""
        allowed_methods = {"form", "basic", "bearer", "api_key"}
        if v not in allowed_methods:
            raise ValueError(f"Authentication method must be one of: {allowed_methods}")
        return v


# Type alias for all source types
AnySource = (
    HTTPSource
    | FTPSource
    | SFTPSource
    | S3Source
    | LocalFileSource
    | VendorPortalSource
)
