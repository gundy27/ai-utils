"""Basic tests for the downloader module."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from gundy_ai.downloader import UniversalDownloader
from gundy_ai.downloader.base import DownloadStatus
from gundy_ai.downloader.sources import HTTPSource, LocalFileSource


class TestUniversalDownloader:
    """Test UniversalDownloader functionality."""

    @pytest.fixture
    def downloader(self):
        """Create a downloader instance for testing."""
        return UniversalDownloader(
            max_retries=1,
            timeout_seconds=30,
            max_concurrent_downloads=1,
            rate_limit_per_second=10.0,
        )

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self, downloader):
        """Test downloader initialization."""
        assert downloader.max_retries == 1
        assert downloader.timeout_seconds == 30
        assert len(downloader.downloaders) == 5  # HTTP, FTP, SFTP, S3, Local

    def test_find_downloader_http(self, downloader):
        """Test finding HTTP downloader."""
        source = HTTPSource(identifier="test", url="https://example.com/file.pdf")
        downloader_instance = downloader._find_downloader(source)
        assert downloader_instance is not None
        assert downloader_instance.can_handle(source)

    def test_find_downloader_local(self, downloader):
        """Test finding local file downloader."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"test content")
            tmp.flush()

            source = LocalFileSource(identifier="test", file_path=tmp.name)
            downloader_instance = downloader._find_downloader(source)
            assert downloader_instance is not None
            assert downloader_instance.can_handle(source)

            # Clean up
            Path(tmp.name).unlink()

    def test_generate_filename_http(self, downloader):
        """Test filename generation for HTTP sources."""
        source = HTTPSource(identifier="test", url="https://example.com/document.pdf")
        filename = downloader._generate_filename(source)
        assert filename == "document.pdf"

        # Test URL without filename
        source = HTTPSource(identifier="test", url="https://example.com/")
        filename = downloader._generate_filename(source)
        assert filename == "download_test"

    def test_generate_filename_local(self, downloader):
        """Test filename generation for local sources."""
        source = LocalFileSource(identifier="test", file_path="/path/to/file.pdf")
        filename = downloader._generate_filename(source)
        assert filename == "file.pdf"

    @pytest.mark.asyncio
    async def test_download_local_file(self, downloader, temp_dir):
        """Test downloading a local file."""
        # Create test file
        source_file = temp_dir / "source.txt"
        source_file.write_text("test content")

        # Create source
        source = LocalFileSource(
            identifier="test",
            file_path=str(source_file),
            move_file=False,
        )

        # Download
        destination = temp_dir / "destination.txt"
        result = await downloader.download(source, destination)

        # Verify result
        assert result.success
        assert result.status == DownloadStatus.COMPLETED
        assert result.local_file is not None
        assert result.local_file.path == destination
        assert result.local_file.verify_checksum()
        assert destination.exists()
        assert destination.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_download_multiple_local_files(self, downloader, temp_dir):
        """Test downloading multiple local files."""
        # Create test files
        source_files = []
        sources = []

        for i in range(3):
            source_file = temp_dir / f"source_{i}.txt"
            source_file.write_text(f"content {i}")
            source_files.append(source_file)

            source = LocalFileSource(
                identifier=f"test_{i}",
                file_path=str(source_file),
                move_file=False,
            )
            sources.append(source)

        # Download multiple files
        results = await downloader.download_multiple(sources, temp_dir)

        # Verify results
        assert len(results) == 3
        for i, (_identifier, result) in enumerate(results.items()):
            assert result.success
            assert result.local_file.path.name == f"source_{i}.txt"

    @pytest.mark.asyncio
    async def test_download_nonexistent_file(self, downloader, temp_dir):
        """Test downloading a nonexistent file."""
        source = LocalFileSource(
            identifier="test",
            file_path="/nonexistent/file.txt",
            move_file=False,
        )

        result = await downloader.download(source, temp_dir / "output.txt")

        assert not result.success
        assert result.status == DownloadStatus.FAILED
        assert "not found" in result.error.lower()

    def test_get_stats(self, downloader):
        """Test getting downloader statistics."""
        stats = downloader.get_stats()

        assert "max_retries" in stats
        assert "timeout_seconds" in stats
        assert "available_downloaders" in stats
        assert "rate_limiter_stats" in stats
        assert len(stats["available_downloaders"]) == 5

    @pytest.mark.asyncio
    async def test_http_download_mock(self, downloader, temp_dir):
        """Test HTTP download with mocked response."""
        source = HTTPSource(identifier="test", url="https://example.com/test.pdf")

        # Mock HTTP response
        mock_content = b"PDF content"

        with patch("aiohttp.ClientSession.request") as mock_request:
            # Mock response object
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.read.return_value = mock_content
            mock_response.headers = {"Content-Length": str(len(mock_content))}

            # Mock context manager
            mock_request.return_value.__aenter__.return_value = mock_response

            # Download
            destination = temp_dir / "test.pdf"
            result = await downloader.download(source, destination)

            # Verify
            assert result.success
            assert result.bytes_downloaded == len(mock_content)
            assert destination.exists()
            assert destination.read_bytes() == mock_content


class TestFileChecksum:
    """Test file checksum functionality."""

    def test_compute_file_hash(self, temp_dir):
        """Test computing file hash."""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello world")

        # Compute hash
        from gundy_ai.downloader.base import FileChecksum

        checksum = FileChecksum.compute_file_hash(test_file)

        assert checksum.algorithm == "sha256"
        assert len(checksum.value) == 64  # SHA256 hex length
        assert checksum.size_bytes == len("hello world")

    def test_verify_checksum(self, temp_dir):
        """Test checksum verification."""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_file.write_text("hello world")

        # Compute and verify hash
        from gundy_ai.downloader.base import FileChecksum

        checksum = FileChecksum.compute_file_hash(test_file)

        assert checksum.verify(test_file)

        # Modify file and verify fails
        test_file.write_text("modified content")
        assert not checksum.verify(test_file)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)
