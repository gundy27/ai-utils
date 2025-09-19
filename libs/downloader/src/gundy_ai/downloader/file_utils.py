"""File utilities for download operations."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import aiofiles
import structlog

from .base import FileChecksum, LocalFile

logger = structlog.get_logger(__name__)


class FileUtils:
    """Utility class for file operations."""

    @staticmethod
    async def ensure_directory(path: str | Path) -> Path:
        """Ensure directory exists, create if necessary."""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    async def safe_filename(filename: str) -> str:
        """Create a safe filename by removing/replacing invalid characters."""
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        safe_name = filename

        for char in invalid_chars:
            safe_name = safe_name.replace(char, "_")

        # Remove leading/trailing spaces and dots
        safe_name = safe_name.strip(" .")

        # Ensure filename is not empty
        if not safe_name:
            safe_name = "unnamed_file"

        # Limit length (Windows has 255 char limit for filename)
        if len(safe_name) > 200:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[: 200 - len(ext)] + ext

        return safe_name

    @staticmethod
    async def get_unique_filename(directory: str | Path, filename: str) -> Path:
        """Get a unique filename in the directory."""
        directory = Path(directory)
        filename = await FileUtils.safe_filename(filename)
        file_path = directory / filename

        if not file_path.exists():
            return file_path

        # File exists, find a unique name
        name, ext = os.path.splitext(filename)
        counter = 1

        while True:
            new_filename = f"{name}_{counter}{ext}"
            new_path = directory / new_filename

            if not new_path.exists():
                return new_path

            counter += 1

    @staticmethod
    async def copy_file(
        source: str | Path,
        destination: str | Path,
        preserve_metadata: bool = True,
    ) -> LocalFile:
        """Copy a file from source to destination."""
        source = Path(source)
        destination = Path(destination)

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        # Ensure destination directory exists
        await FileUtils.ensure_directory(destination.parent)

        # Copy the file
        if preserve_metadata:
            shutil.copy2(source, destination)
        else:
            shutil.copy(source, destination)

        # Compute checksum
        checksum = FileChecksum.compute_file_hash(destination)

        return LocalFile(
            path=destination,
            checksum=checksum,
            metadata={
                "source_path": str(source),
                "operation": "copy",
                "preserve_metadata": preserve_metadata,
            },
        )

    @staticmethod
    async def move_file(
        source: str | Path,
        destination: str | Path,
        preserve_metadata: bool = True,
    ) -> LocalFile:
        """Move a file from source to destination."""
        source = Path(source)
        destination = Path(destination)

        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        # Ensure destination directory exists
        await FileUtils.ensure_directory(destination.parent)

        # Move the file
        if preserve_metadata:
            shutil.move(str(source), str(destination))
        else:
            shutil.move(str(source), str(destination))

        # Compute checksum
        checksum = FileChecksum.compute_file_hash(destination)

        return LocalFile(
            path=destination,
            checksum=checksum,
            metadata={
                "source_path": str(source),
                "operation": "move",
                "preserve_metadata": preserve_metadata,
            },
        )

    @staticmethod
    async def write_file_async(
        file_path: str | Path,
        content: bytes,
        mode: str = "wb",
    ) -> LocalFile:
        """Write content to file asynchronously."""
        file_path = Path(file_path)

        # Ensure directory exists
        await FileUtils.ensure_directory(file_path.parent)

        # Write file
        async with aiofiles.open(file_path, mode) as f:
            await f.write(content)

        # Compute checksum
        checksum = FileChecksum.compute_file_hash(file_path)

        return LocalFile(
            path=file_path,
            checksum=checksum,
            metadata={"operation": "write", "content_size": len(content), "mode": mode},
        )

    @staticmethod
    async def read_file_async(file_path: str | Path, mode: str = "rb") -> bytes:
        """Read file content asynchronously."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        async with aiofiles.open(file_path, mode) as f:
            return await f.read()

    @staticmethod
    def get_file_size(file_path: str | Path) -> int:
        """Get file size in bytes."""
        return Path(file_path).stat().st_size

    @staticmethod
    def file_exists(file_path: str | Path) -> bool:
        """Check if file exists."""
        return Path(file_path).exists()

    @staticmethod
    async def delete_file(file_path: str | Path) -> bool:
        """Delete a file."""
        try:
            Path(file_path).unlink()
            return True
        except Exception as e:
            logger.error("file.delete.error", path=str(file_path), error=str(e))
            return False

    @staticmethod
    async def cleanup_temp_files(directory: str | Path, pattern: str = "*.tmp") -> int:
        """Clean up temporary files in directory."""
        directory = Path(directory)
        if not directory.exists():
            return 0

        temp_files = list(directory.glob(pattern))
        deleted_count = 0

        for temp_file in temp_files:
            try:
                temp_file.unlink()
                deleted_count += 1
            except Exception as e:
                logger.warning(
                    "temp_file.delete.error",
                    path=str(temp_file),
                    error=str(e),
                )

        logger.info("temp_files.cleaned", count=deleted_count, directory=str(directory))
        return deleted_count
