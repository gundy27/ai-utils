"""Parquet output writer for efficient columnar storage."""

import time
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..document import ProcessedDocument
from .base import OutputFormat, OutputResult, OutputWriter


class ParquetWriter(OutputWriter):
    """Writer for Parquet format output."""

    def __init__(
        self,
        compression: str = "snappy",
        chunk_per_row: bool = True,
        include_full_text: bool = False,
        **kwargs: Any,
    ):
        """Initialize Parquet writer.

        Args:
            compression: Compression algorithm (snappy, gzip, lz4, brotli)
            chunk_per_row: If True, each chunk becomes a row. If False, each document becomes a row.
            include_full_text: Whether to include full document text in output
        """
        super().__init__(OutputFormat.PARQUET, **kwargs)
        self.compression = compression
        self.chunk_per_row = chunk_per_row
        self.include_full_text = include_full_text

    async def write_document(
        self, document: ProcessedDocument, output_path: str | Path, **kwargs: Any
    ) -> OutputResult:
        """Write a single document as Parquet."""
        start_time = time.time()

        try:
            # Convert document to DataFrame
            df = self._document_to_dataframe(document)

            # Write to Parquet file
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Use PyArrow for better control over schema and performance
            table = pa.Table.from_pandas(df)
            pq.write_table(
                table,
                path,
                compression=self.compression,
                write_statistics=True,
                use_dictionary=True,  # Enable dictionary encoding for string columns
            )

            processing_time = (time.time() - start_time) * 1000

            return self._create_result(
                success=True,
                output_path=path,
                processing_time_ms=processing_time,
                document_count=1,
                chunk_count=len(document.chunks),
                row_count=len(df),
                compression=self.compression,
                file_size=path.stat().st_size,
            )

        except Exception as e:
            self.logger.error(
                "parquet_write_error", error=str(e), output_path=str(output_path)
            )
            return self._create_result(
                success=False,
                error=f"Parquet write failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def write_documents(
        self, documents: list[ProcessedDocument], output_path: str | Path, **kwargs: Any
    ) -> OutputResult:
        """Write multiple documents as Parquet."""
        start_time = time.time()

        try:
            # Convert all documents to DataFrames and concatenate
            dfs = [self._document_to_dataframe(doc) for doc in documents]
            combined_df = pd.concat(dfs, ignore_index=True)

            # Write to Parquet file
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            table = pa.Table.from_pandas(combined_df)
            pq.write_table(
                table,
                path,
                compression=self.compression,
                write_statistics=True,
                use_dictionary=True,
            )

            processing_time = (time.time() - start_time) * 1000
            total_chunks = sum(len(doc.chunks) for doc in documents)

            return self._create_result(
                success=True,
                output_path=path,
                processing_time_ms=processing_time,
                document_count=len(documents),
                chunk_count=total_chunks,
                row_count=len(combined_df),
                compression=self.compression,
                file_size=path.stat().st_size,
            )

        except Exception as e:
            self.logger.error(
                "parquet_write_error", error=str(e), output_path=str(output_path)
            )
            return self._create_result(
                success=False,
                error=f"Parquet write failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _document_to_dataframe(self, document: ProcessedDocument) -> pd.DataFrame:
        """Convert ProcessedDocument to pandas DataFrame."""
        if self.chunk_per_row:
            return self._chunks_to_dataframe(document)
        else:
            return self._document_to_single_row(document)

    def _chunks_to_dataframe(self, document: ProcessedDocument) -> pd.DataFrame:
        """Convert document chunks to DataFrame with one row per chunk."""
        rows = []

        for chunk in document.chunks:
            row = {
                # Document metadata
                "document_filename": document.metadata.filename,
                "document_type": document.metadata.document_type.value,
                "document_size_bytes": document.metadata.size_bytes,
                "document_page_count": document.metadata.page_count,
                "document_word_count": document.metadata.word_count,
                "document_language": document.metadata.language,
                "document_created_at": document.metadata.created_at,
                "document_modified_at": document.metadata.modified_at,
                # Chunk data
                "chunk_content": chunk.content,
                "chunk_index": chunk.chunk_index,
                "chunk_start_char": chunk.start_char,
                "chunk_end_char": chunk.end_char,
                "chunk_token_count": chunk.token_count,
                # Processing metadata (flattened)
                **self._flatten_metadata(
                    document.metadata.custom_metadata, "document_"
                ),
                **self._flatten_metadata(chunk.metadata, "chunk_"),
            }

            # Add full text if requested
            if self.include_full_text:
                row["document_full_text"] = document.full_text

            rows.append(row)

        return pd.DataFrame(rows)

    def _document_to_single_row(self, document: ProcessedDocument) -> pd.DataFrame:
        """Convert entire document to single DataFrame row."""
        row = {
            # Document metadata
            "filename": document.metadata.filename,
            "document_type": document.metadata.document_type.value,
            "size_bytes": document.metadata.size_bytes,
            "page_count": document.metadata.page_count,
            "word_count": document.metadata.word_count,
            "language": document.metadata.language,
            "created_at": document.metadata.created_at,
            "modified_at": document.metadata.modified_at,
            # Document content
            "full_text": document.full_text,
            # Statistics
            "chunk_count": document.get_chunk_count(),
            "total_tokens": document.get_total_tokens(),
            "text_length": len(document.full_text),
            # Chunks as JSON string (for single-row format)
            "chunks_json": pd.Series(
                [
                    {
                        "content": chunk.content,
                        "chunk_index": chunk.chunk_index,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "token_count": chunk.token_count,
                        "metadata": chunk.metadata,
                    }
                    for chunk in document.chunks
                ]
            ).to_json(),
            # Processing metadata (flattened)
            **self._flatten_metadata(document.metadata.custom_metadata, ""),
        }

        return pd.DataFrame([row])

    def _flatten_metadata(
        self, metadata: dict[str, Any], prefix: str = ""
    ) -> dict[str, Any]:
        """Flatten nested metadata dictionary for columnar storage."""
        flattened = {}

        for key, value in metadata.items():
            column_name = f"{prefix}{key}"

            # Handle nested dictionaries
            if isinstance(value, dict):
                flattened.update(self._flatten_metadata(value, f"{column_name}_"))
            # Handle lists by converting to JSON string
            elif isinstance(value, list):
                flattened[column_name] = str(value) if value else None
            # Handle other types
            else:
                flattened[column_name] = value

        return flattened
