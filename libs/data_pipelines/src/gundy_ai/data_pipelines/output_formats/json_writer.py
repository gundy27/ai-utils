"""JSON and NDJSON output writers."""

import json
import time
from pathlib import Path
from typing import Any

import aiofiles

from ..document import ProcessedDocument
from .base import OutputFormat, OutputResult, OutputWriter


class JSONWriter(OutputWriter):
    """Writer for JSON format output."""

    def __init__(self, indent: int = 2, ensure_ascii: bool = False, **kwargs: Any):
        """Initialize JSON writer.

        Args:
            indent: JSON indentation level
            ensure_ascii: Whether to escape non-ASCII characters
        """
        super().__init__(OutputFormat.JSON, **kwargs)
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    async def write_document(
        self, document: ProcessedDocument, output_path: str | Path, **kwargs: Any
    ) -> OutputResult:
        """Write a single document as JSON."""
        start_time = time.time()

        try:
            # Convert document to dictionary
            doc_data = self._document_to_dict(document)

            # Write to file
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                json_str = json.dumps(
                    doc_data,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii,
                    default=str,  # Handle datetime and other non-serializable types
                )
                await f.write(json_str)

            processing_time = (time.time() - start_time) * 1000

            return self._create_result(
                success=True,
                output_path=path,
                processing_time_ms=processing_time,
                document_count=1,
                chunk_count=len(document.chunks),
                file_size=path.stat().st_size,
            )

        except Exception as e:
            self.logger.error(
                "json_write_error", error=str(e), output_path=str(output_path)
            )
            return self._create_result(
                success=False,
                error=f"JSON write failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def write_documents(
        self, documents: list[ProcessedDocument], output_path: str | Path, **kwargs: Any
    ) -> OutputResult:
        """Write multiple documents as JSON array."""
        start_time = time.time()

        try:
            # Convert all documents to dictionaries
            docs_data = [self._document_to_dict(doc) for doc in documents]

            # Write to file
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                json_str = json.dumps(
                    docs_data,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii,
                    default=str,
                )
                await f.write(json_str)

            processing_time = (time.time() - start_time) * 1000
            total_chunks = sum(len(doc.chunks) for doc in documents)

            return self._create_result(
                success=True,
                output_path=path,
                processing_time_ms=processing_time,
                document_count=len(documents),
                chunk_count=total_chunks,
                file_size=path.stat().st_size,
            )

        except Exception as e:
            self.logger.error(
                "json_write_error", error=str(e), output_path=str(output_path)
            )
            return self._create_result(
                success=False,
                error=f"JSON write failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _document_to_dict(self, document: ProcessedDocument) -> dict[str, Any]:
        """Convert ProcessedDocument to dictionary."""
        return {
            "metadata": {
                "filename": document.metadata.filename,
                "document_type": document.metadata.document_type.value,
                "size_bytes": document.metadata.size_bytes,
                "page_count": document.metadata.page_count,
                "word_count": document.metadata.word_count,
                "language": document.metadata.language,
                "created_at": document.metadata.created_at,
                "modified_at": document.metadata.modified_at,
                "custom_metadata": document.metadata.custom_metadata,
            },
            "full_text": document.full_text,
            "chunks": [
                {
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata,
                }
                for chunk in document.chunks
            ],
            "statistics": {
                "chunk_count": document.get_chunk_count(),
                "total_tokens": document.get_total_tokens(),
                "text_length": len(document.full_text),
            },
        }


class NDJSONWriter(OutputWriter):
    """Writer for NDJSON (Newline Delimited JSON) format."""

    def __init__(self, chunk_per_line: bool = True, **kwargs: Any):
        """Initialize NDJSON writer.

        Args:
            chunk_per_line: If True, write each chunk as a separate line.
                           If False, write each document as a separate line.
        """
        super().__init__(OutputFormat.NDJSON, **kwargs)
        self.chunk_per_line = chunk_per_line

    async def write_document(
        self, document: ProcessedDocument, output_path: str | Path, **kwargs: Any
    ) -> OutputResult:
        """Write a single document as NDJSON."""
        start_time = time.time()

        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            lines_written = 0

            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                if self.chunk_per_line:
                    # Write each chunk as a separate line
                    for chunk in document.chunks:
                        chunk_data = self._chunk_to_dict(chunk, document)
                        json_line = json.dumps(
                            chunk_data, ensure_ascii=False, default=str
                        )
                        await f.write(json_line + "\n")
                        lines_written += 1
                else:
                    # Write entire document as one line
                    doc_data = self._document_to_dict(document)
                    json_line = json.dumps(doc_data, ensure_ascii=False, default=str)
                    await f.write(json_line + "\n")
                    lines_written = 1

            processing_time = (time.time() - start_time) * 1000

            return self._create_result(
                success=True,
                output_path=path,
                processing_time_ms=processing_time,
                document_count=1,
                chunk_count=len(document.chunks),
                lines_written=lines_written,
                file_size=path.stat().st_size,
            )

        except Exception as e:
            self.logger.error(
                "ndjson_write_error", error=str(e), output_path=str(output_path)
            )
            return self._create_result(
                success=False,
                error=f"NDJSON write failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def write_documents(
        self, documents: list[ProcessedDocument], output_path: str | Path, **kwargs: Any
    ) -> OutputResult:
        """Write multiple documents as NDJSON."""
        start_time = time.time()

        try:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            lines_written = 0
            total_chunks = 0

            async with aiofiles.open(path, "w", encoding="utf-8") as f:
                for document in documents:
                    total_chunks += len(document.chunks)

                    if self.chunk_per_line:
                        # Write each chunk as a separate line
                        for chunk in document.chunks:
                            chunk_data = self._chunk_to_dict(chunk, document)
                            json_line = json.dumps(
                                chunk_data, ensure_ascii=False, default=str
                            )
                            await f.write(json_line + "\n")
                            lines_written += 1
                    else:
                        # Write entire document as one line
                        doc_data = self._document_to_dict(document)
                        json_line = json.dumps(
                            doc_data, ensure_ascii=False, default=str
                        )
                        await f.write(json_line + "\n")
                        lines_written += 1

            processing_time = (time.time() - start_time) * 1000

            return self._create_result(
                success=True,
                output_path=path,
                processing_time_ms=processing_time,
                document_count=len(documents),
                chunk_count=total_chunks,
                lines_written=lines_written,
                file_size=path.stat().st_size,
            )

        except Exception as e:
            self.logger.error(
                "ndjson_write_error", error=str(e), output_path=str(output_path)
            )
            return self._create_result(
                success=False,
                error=f"NDJSON write failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _document_to_dict(self, document: ProcessedDocument) -> dict[str, Any]:
        """Convert ProcessedDocument to dictionary (same as JSONWriter)."""
        return {
            "metadata": {
                "filename": document.metadata.filename,
                "document_type": document.metadata.document_type.value,
                "size_bytes": document.metadata.size_bytes,
                "page_count": document.metadata.page_count,
                "word_count": document.metadata.word_count,
                "language": document.metadata.language,
                "created_at": document.metadata.created_at,
                "modified_at": document.metadata.modified_at,
                "custom_metadata": document.metadata.custom_metadata,
            },
            "full_text": document.full_text,
            "chunks": [
                {
                    "content": chunk.content,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "token_count": chunk.token_count,
                    "metadata": chunk.metadata,
                }
                for chunk in document.chunks
            ],
            "statistics": {
                "chunk_count": document.get_chunk_count(),
                "total_tokens": document.get_total_tokens(),
                "text_length": len(document.full_text),
            },
        }

    def _chunk_to_dict(self, chunk, document: ProcessedDocument) -> dict[str, Any]:
        """Convert a single chunk to dictionary with document context."""
        return {
            "document_metadata": {
                "filename": document.metadata.filename,
                "document_type": document.metadata.document_type.value,
                "size_bytes": document.metadata.size_bytes,
                "page_count": document.metadata.page_count,
                "word_count": document.metadata.word_count,
                "custom_metadata": document.metadata.custom_metadata,
            },
            "chunk": {
                "content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
                "token_count": chunk.token_count,
                "metadata": chunk.metadata,
            },
        }
