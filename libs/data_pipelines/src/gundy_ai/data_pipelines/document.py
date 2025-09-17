"""Document processing and text chunking utilities."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from docx import Document as DocxDocument
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
import tiktoken

from .base import BaseProcessor, ProcessingResult, ProcessorConfig

logger = structlog.get_logger(__name__)


class DocumentType(Enum):
    """Supported document types."""

    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    MARKDOWN = "md"


class ChunkingStrategy(Enum):
    """Text chunking strategies."""

    FIXED_SIZE = "fixed_size"
    SENTENCE_BOUNDARY = "sentence_boundary"
    PARAGRAPH_BOUNDARY = "paragraph_boundary"
    SEMANTIC = "semantic"


@dataclass
class TextChunk:
    """A chunk of text with metadata."""

    content: str
    chunk_index: int
    start_char: int
    end_char: int
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate chunk data."""
        if self.start_char < 0:
            raise ValueError("start_char must be non-negative")
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        if self.token_count < 0:
            raise ValueError("token_count must be non-negative")


@dataclass
class DocumentMetadata:
    """Metadata for a document."""

    filename: str
    document_type: DocumentType
    size_bytes: int
    page_count: int | None = None
    word_count: int | None = None
    language: str | None = None
    created_at: str | None = None
    modified_at: str | None = None
    custom_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedDocument:
    """A processed document with chunks."""

    metadata: DocumentMetadata
    chunks: list[TextChunk]
    full_text: str

    def get_chunk_count(self) -> int:
        """Get total number of chunks."""
        return len(self.chunks)

    def get_total_tokens(self) -> int:
        """Get total token count across all chunks."""
        return sum(chunk.token_count for chunk in self.chunks)


class DocumentProcessor(BaseProcessor[str, ProcessedDocument]):
    """Processor for extracting text from various document formats."""

    def __init__(self, config: ProcessorConfig):
        """Initialize document processor."""
        super().__init__(config)
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def validate_input(self, input_data: str) -> bool:
        """Validate input is a valid file path."""
        if not isinstance(input_data, str):
            return False
        path = Path(input_data)
        return path.exists() and path.is_file()

    async def process(self, file_path: str) -> ProcessingResult[ProcessedDocument]:
        """Process a document file and extract text."""
        try:
            path = Path(file_path)
            document_type = self._detect_document_type(path)

            # Extract text based on document type
            if document_type == DocumentType.TXT:
                text = await self._extract_txt(path)
            elif document_type == DocumentType.PDF:
                text = await self._extract_pdf(path)
            elif document_type == DocumentType.DOCX:
                text = await self._extract_docx(path)
            elif document_type == DocumentType.HTML:
                text = await self._extract_html(path)
            elif document_type == DocumentType.MARKDOWN:
                text = await self._extract_markdown(path)
            else:
                return ProcessingResult(
                    success=False, error=f"Unsupported document type: {document_type}"
                )

            # Clean and normalize text
            cleaned_text = self._clean_text(text)

            # Create metadata
            metadata = DocumentMetadata(
                filename=path.name,
                document_type=document_type,
                size_bytes=path.stat().st_size,
                word_count=len(cleaned_text.split()),
                custom_metadata={"file_path": str(path), "file_extension": path.suffix},
            )

            # Create processed document
            processed_doc = ProcessedDocument(
                metadata=metadata,
                chunks=[],  # Will be populated by chunking processor
                full_text=cleaned_text,
            )

            return ProcessingResult(
                success=True,
                data=processed_doc,
                metadata={
                    "document_type": document_type.value,
                    "text_length": len(cleaned_text),
                    "word_count": metadata.word_count,
                },
            )

        except Exception as e:
            self.logger.error(
                "document.processing.error", error=str(e), file_path=file_path
            )
            return ProcessingResult(
                success=False, error=f"Failed to process document: {str(e)}"
            )

    def _detect_document_type(self, path: Path) -> DocumentType:
        """Detect document type from file extension."""
        suffix = path.suffix.lower()

        if suffix == ".txt":
            return DocumentType.TXT
        elif suffix == ".pdf":
            return DocumentType.PDF
        elif suffix in [".docx", ".doc"]:
            return DocumentType.DOCX
        elif suffix in [".html", ".htm"]:
            return DocumentType.HTML
        elif suffix in [".md", ".markdown"]:
            return DocumentType.MARKDOWN
        else:
            raise ValueError(f"Unsupported file extension: {suffix}")

    async def _extract_txt(self, path: Path) -> str:
        """Extract text from plain text file."""
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: path.read_text(encoding="utf-8", errors="replace")
        )

    async def _extract_pdf(self, path: Path) -> str:
        """Extract text from PDF file."""

        def _extract():
            with open(path, "rb") as file:
                reader = PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text

        return await asyncio.get_event_loop().run_in_executor(None, _extract)

    async def _extract_docx(self, path: Path) -> str:
        """Extract text from DOCX file."""

        def _extract():
            doc = DocxDocument(path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text

        return await asyncio.get_event_loop().run_in_executor(None, _extract)

    async def _extract_html(self, path: Path) -> str:
        """Extract text from HTML file."""

        def _extract():
            with open(path, "r", encoding="utf-8", errors="replace") as file:
                soup = BeautifulSoup(file.read(), "html.parser")
                return soup.get_text()

        return await asyncio.get_event_loop().run_in_executor(None, _extract)

    async def _extract_markdown(self, path: Path) -> str:
        """Extract text from Markdown file."""
        # For now, just return raw markdown
        # Could be enhanced to strip markdown syntax
        return await self._extract_txt(path)

    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text."""
        # Remove excessive whitespace
        text = re.sub(r"\s+", " ", text)

        # Remove special characters that might cause issues
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        # Normalize line breaks
        text = re.sub(r"\r\n|\r", "\n", text)

        return text.strip()


class TextChunker(BaseProcessor[ProcessedDocument, ProcessedDocument]):
    """Processor for chunking text into smaller pieces."""

    def __init__(
        self,
        config: ProcessorConfig,
        strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE,
        chunk_size: int = 1000,
        overlap: int = 200,
    ):
        """Initialize text chunker."""
        super().__init__(config)
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def validate_input(self, input_data: ProcessedDocument) -> bool:
        """Validate input is a processed document."""
        return isinstance(input_data, ProcessedDocument)

    async def process(
        self, document: ProcessedDocument
    ) -> ProcessingResult[ProcessedDocument]:
        """Chunk the document text."""
        try:
            chunks = await self._chunk_text(document.full_text)

            # Update document with chunks
            document.chunks = chunks

            return ProcessingResult(
                success=True,
                data=document,
                metadata={
                    "chunk_count": len(chunks),
                    "strategy": self.strategy.value,
                    "chunk_size": self.chunk_size,
                    "overlap": self.overlap,
                },
            )

        except Exception as e:
            self.logger.error("chunking.error", error=str(e))
            return ProcessingResult(
                success=False, error=f"Failed to chunk text: {str(e)}"
            )

    async def _chunk_text(self, text: str) -> list[TextChunk]:
        """Chunk text based on strategy."""
        if self.strategy == ChunkingStrategy.FIXED_SIZE:
            return await self._chunk_by_token_count(text)
        elif self.strategy == ChunkingStrategy.SENTENCE_BOUNDARY:
            return await self._chunk_by_sentences(text)
        elif self.strategy == ChunkingStrategy.PARAGRAPH_BOUNDARY:
            return await self._chunk_by_paragraphs(text)
        else:
            raise ValueError(f"Unsupported chunking strategy: {self.strategy}")

    async def _chunk_by_token_count(self, text: str) -> list[TextChunk]:
        """Chunk text by token count."""
        tokens = self.encoding.encode(text)
        chunks = []

        start_token = 0
        chunk_index = 0

        while start_token < len(tokens):
            end_token = min(start_token + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start_token:end_token]

            # Decode tokens back to text
            chunk_text = self.encoding.decode(chunk_tokens)

            # Find character boundaries
            start_char = self._find_char_boundary(text, tokens[:start_token])
            end_char = self._find_char_boundary(text, tokens[:end_token])

            chunk = TextChunk(
                content=chunk_text,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=end_char,
                token_count=len(chunk_tokens),
                metadata={"chunking_strategy": "fixed_size"},
            )

            chunks.append(chunk)
            chunk_index += 1

            # Move start position with overlap
            start_token = end_token - self.overlap
            if start_token >= len(tokens):
                break

        return chunks

    async def _chunk_by_sentences(self, text: str) -> list[TextChunk]:
        """Chunk text by sentence boundaries."""
        # Simple sentence splitting
        sentences = re.split(r"[.!?]+", text)
        chunks = []
        current_chunk = ""
        chunk_index = 0
        start_char = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence would exceed chunk size
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            test_tokens = self.encoding.encode(test_chunk)

            if len(test_tokens) > self.chunk_size and current_chunk:
                # Create chunk from current content
                end_char = start_char + len(current_chunk)
                chunk = TextChunk(
                    content=current_chunk.strip(),
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    token_count=len(self.encoding.encode(current_chunk)),
                    metadata={"chunking_strategy": "sentence_boundary"},
                )
                chunks.append(chunk)

                # Start new chunk
                chunk_index += 1
                start_char = end_char
                current_chunk = sentence
            else:
                current_chunk = test_chunk

        # Add final chunk if there's content
        if current_chunk.strip():
            end_char = start_char + len(current_chunk)
            chunk = TextChunk(
                content=current_chunk.strip(),
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=end_char,
                token_count=len(self.encoding.encode(current_chunk)),
                metadata={"chunking_strategy": "sentence_boundary"},
            )
            chunks.append(chunk)

        return chunks

    async def _chunk_by_paragraphs(self, text: str) -> list[TextChunk]:
        """Chunk text by paragraph boundaries."""
        paragraphs = text.split("\n\n")
        chunks = []
        chunk_index = 0
        start_char = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # Check if paragraph fits in chunk size
            tokens = self.encoding.encode(paragraph)

            if len(tokens) > self.chunk_size:
                # Split large paragraph by sentences
                sentence_chunks = await self._chunk_by_sentences(paragraph)
                for sentence_chunk in sentence_chunks:
                    sentence_chunk.chunk_index = chunk_index
                    sentence_chunk.start_char = start_char
                    sentence_chunk.end_char = start_char + len(sentence_chunk.content)
                    sentence_chunk.metadata["chunking_strategy"] = "paragraph_boundary"
                    chunks.append(sentence_chunk)
                    chunk_index += 1
                    start_char = sentence_chunk.end_char
            else:
                # Use entire paragraph as chunk
                end_char = start_char + len(paragraph)
                chunk = TextChunk(
                    content=paragraph,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=end_char,
                    token_count=len(tokens),
                    metadata={"chunking_strategy": "paragraph_boundary"},
                )
                chunks.append(chunk)
                chunk_index += 1
                start_char = end_char

        return chunks

    def _find_char_boundary(self, text: str, tokens: list[int]) -> int:
        """Find character position corresponding to token position."""
        if not tokens:
            return 0

        # Approximate character position
        token_text = self.encoding.decode(tokens)
        return text.find(token_text)
