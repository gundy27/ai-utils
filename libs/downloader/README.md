# Gundy AI Downloader

A universal file downloader with support for multiple source types including HTTP/HTTPS, FTP, SFTP, AWS S3, and local files. Features retry logic, rate limiting, file integrity verification, and concurrent downloads.

## Features

- **Multiple Source Types**: HTTP/HTTPS, FTP, SFTP, AWS S3, local files
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Rate Limiting**: Per-second and per-domain rate limiting
- **Concurrent Downloads**: Configurable concurrent download limits
- **File Integrity**: SHA256 checksum verification
- **CLI Interface**: Command-line tool for easy usage
- **Async/Await**: Full async support for high-performance downloads

## Installation

```bash
pip install gundy-ai-downloader
```

## Quick Start

### Python API

```python
import asyncio
from gundy_ai.downloader import UniversalDownloader
from gundy_ai.downloader.sources import HTTPSource

async def main():
    # Create downloader
    downloader = UniversalDownloader(
        max_retries=3,
        timeout_seconds=300,
        max_concurrent_downloads=5,
        rate_limit_per_second=2.0
    )

    # Create HTTP source
    source = HTTPSource(
        identifier="example-doc",
        url="https://example.com/document.pdf",
        headers={"User-Agent": "MyApp/1.0"}
    )

    # Download file
    result = await downloader.download(
        source=source,
        destination="./downloads/",
        filename="document.pdf"
    )

    if result.success:
        print(f"Downloaded: {result.local_file.path}")
        print(f"Checksum: {result.local_file.checksum.value}")
    else:
        print(f"Download failed: {result.error}")

asyncio.run(main())
```

### Command Line Interface

```bash
# Download from HTTP URL
ai-downloader http --url "https://example.com/file.pdf" --destination ./downloads/

# Download from S3
ai-downloader s3 --bucket my-bucket --key path/to/file.pdf --region us-west-2

# Copy local file
ai-downloader local --source-path /path/to/source.pdf --destination ./downloads/

# Batch download from JSON config
ai-downloader batch --config downloads.json
```

## Source Types

### HTTP/HTTPS Sources

```python
from gundy_ai.downloader.sources import HTTPSource

source = HTTPSource(
    identifier="unique-id",
    url="https://example.com/file.pdf",
    headers={"Authorization": "Bearer token"},
    auth={"username": "user", "password": "pass"},
    method="GET",
    timeout=300,
    verify_ssl=True
)
```

### AWS S3 Sources

```python
from gundy_ai.downloader.sources import S3Source

source = S3Source(
    identifier="s3-doc",
    bucket="my-bucket",
    key="path/to/file.pdf",
    region="us-west-2",
    access_key_id="AKIA...",
    secret_access_key="...",
    version_id="optional-version-id"
)
```

### FTP Sources

```python
from gundy_ai.downloader.sources import FTPSource

source = FTPSource(
    identifier="ftp-doc",
    host="ftp.example.com",
    username="user",
    password="pass",
    remote_path="/path/to/file.pdf",
    passive_mode=True,
    binary_mode=True
)
```

### SFTP Sources

```python
from gundy_ai.downloader.sources import SFTPSource

source = SFTPSource(
    identifier="sftp-doc",
    host="sftp.example.com",
    username="user",
    private_key_path="/path/to/private_key",
    remote_path="/path/to/file.pdf"
)
```

### Local File Sources

```python
from gundy_ai.downloader.sources import LocalFileSource

source = LocalFileSource(
    identifier="local-doc",
    file_path="/path/to/source.pdf",
    move_file=False,  # True to move instead of copy
    preserve_metadata=True
)
```

## Advanced Usage

### Batch Downloads

```python
# Download multiple files concurrently
sources = [
    HTTPSource(identifier="doc1", url="https://example.com/doc1.pdf"),
    HTTPSource(identifier="doc2", url="https://example.com/doc2.pdf"),
    S3Source(identifier="doc3", bucket="my-bucket", key="doc3.pdf")
]

results = await downloader.download_multiple(
    sources=sources,
    destination_directory="./downloads/"
)

for identifier, result in results.items():
    if result.success:
        print(f"✓ {identifier}: {result.local_file.path}")
    else:
        print(f"✗ {identifier}: {result.error}")
```

### Custom Rate Limiting

```python
from gundy_ai.downloader import RateLimiter

# Create custom rate limiter
rate_limiter = RateLimiter(
    max_requests_per_second=0.5,  # Very slow rate
    max_concurrent_downloads=2,
    burst_size=3
)

# Set domain-specific limits
rate_limiter.set_domain_rate("api.example.com", 1.0)

downloader = UniversalDownloader(rate_limiter=rate_limiter)
```

### File Integrity Verification

```python
from gundy_ai.downloader.base import FileChecksum

# Verify downloaded file
if result.success and result.local_file:
    if result.local_file.verify_checksum():
        print("File integrity verified ✓")
    else:
        print("File integrity check failed ✗")

# Compute checksum for existing file
checksum = FileChecksum.compute_file_hash("/path/to/file.pdf")
print(f"SHA256: {checksum.value}")
```

## Configuration

### JSON Config for Batch Downloads

```json
[
  {
    "type": "http",
    "id": "doc1",
    "url": "https://example.com/doc1.pdf",
    "headers": { "User-Agent": "MyApp/1.0" }
  },
  {
    "type": "s3",
    "id": "doc2",
    "bucket": "my-bucket",
    "key": "doc2.pdf",
    "region": "us-west-2"
  },
  {
    "type": "local",
    "id": "doc3",
    "file_path": "/path/to/source.pdf",
    "move": false
  }
]
```

### Environment Variables

```bash
# AWS credentials (for S3)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"

# Custom settings
export DOWNLOADER_MAX_RETRIES=5
export DOWNLOADER_TIMEOUT=600
export DOWNLOADER_RATE_LIMIT=2.0
```

## Error Handling

The downloader provides detailed error information:

```python
result = await downloader.download(source, destination)

if not result.success:
    print(f"Error: {result.error}")
    print(f"Status: {result.status}")
    print(f"Metadata: {result.metadata}")
```

Common error scenarios:

- Network timeouts
- Authentication failures
- File not found
- Permission denied
- Checksum verification failures

## Performance Tips

1. **Adjust concurrency**: Increase `max_concurrent_downloads` for better throughput
2. **Rate limiting**: Use appropriate rate limits to avoid overwhelming servers
3. **Timeout settings**: Set reasonable timeouts based on file sizes
4. **Retry logic**: Use exponential backoff for transient failures
5. **Checksum verification**: Disable for very large files if performance is critical

## Development

```bash
# Install development dependencies
poetry install

# Run tests
poetry run pytest

# Format code
poetry run black src/
poetry run isort src/

# Lint code
poetry run ruff check src/
```

## License

MIT License - see LICENSE file for details.
