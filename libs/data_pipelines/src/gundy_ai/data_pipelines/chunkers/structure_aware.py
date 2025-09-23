"""Structure-aware chunking that preserves document hierarchy."""

import re
import time
from typing import Any

import tiktoken

from ..document import ProcessedDocument, TextChunk
from .base import BaseChunker, ChunkingResult


class StructureAwareChunker(BaseChunker):
    """Chunker that preserves document structure like headings and sections."""

    def __init__(
        self,
        max_chunk_size: int = 1000,
        min_chunk_size: int = 100,
        preserve_headings: bool = True,
        preserve_paragraphs: bool = True,
        heading_patterns: list[str] | None = None,
        **kwargs: Any,
    ):
        """Initialize structure-aware chunker.

        Args:
            max_chunk_size: Maximum tokens per chunk
            min_chunk_size: Minimum tokens per chunk
            preserve_headings: Whether to keep headings with their content
            preserve_paragraphs: Whether to avoid breaking paragraphs
            heading_patterns: Regex patterns to identify headings
        """
        super().__init__("structure_aware", **kwargs)

        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.preserve_headings = preserve_headings
        self.preserve_paragraphs = preserve_paragraphs

        # Default heading patterns (Markdown-style and common document patterns)
        self.heading_patterns = heading_patterns or [
            r"^#{1,6}\s+.+$",  # Markdown headings
            r"^[A-Z][A-Z\s]{2,}$",  # ALL CAPS headings
            r"^\d+\.\s+[A-Z].+$",  # Numbered sections
            r"^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:?\s*$",  # Title Case headings
            r"^[IVX]+\.\s+.+$",  # Roman numeral sections
        ]

        self.encoding = tiktoken.get_encoding("cl100k_base")

    async def chunk(self, document: ProcessedDocument) -> ChunkingResult:
        """Chunk document while preserving structure."""
        start_time = time.time()

        try:
            # Split text into structural elements
            elements = await self._parse_document_structure(document.full_text)

            if not elements:
                return ChunkingResult(
                    success=False, error="No structural elements found in document"
                )

            # Group elements into chunks
            chunks = await self._create_structure_aware_chunks(
                elements, document.full_text
            )

            processing_time = (time.time() - start_time) * 1000

            return ChunkingResult(
                success=True,
                chunks=chunks,
                metadata={
                    "element_count": len(elements),
                    "heading_count": sum(
                        1 for elem in elements if elem["type"] == "heading"
                    ),
                    "paragraph_count": sum(
                        1 for elem in elements if elem["type"] == "paragraph"
                    ),
                    "max_chunk_size": self.max_chunk_size,
                    "min_chunk_size": self.min_chunk_size,
                    "preserve_headings": self.preserve_headings,
                    "preserve_paragraphs": self.preserve_paragraphs,
                },
                processing_time_ms=processing_time,
            )

        except Exception as e:
            self.logger.error("structure_aware_chunking_error", error=str(e))
            return ChunkingResult(
                success=False,
                error=f"Structure-aware chunking failed: {str(e)}",
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    async def _parse_document_structure(self, text: str) -> list[dict[str, Any]]:
        """Parse document into structural elements."""
        elements = []
        lines = text.split("\n")

        current_paragraph = []

        for line_num, line in enumerate(lines):
            line = line.strip()

            if not line:
                # Empty line - end current paragraph if exists
                if current_paragraph:
                    paragraph_text = " ".join(current_paragraph)
                    elements.append(
                        {
                            "type": "paragraph",
                            "content": paragraph_text,
                            "line_start": line_num - len(current_paragraph),
                            "line_end": line_num - 1,
                            "level": 0,
                        }
                    )
                    current_paragraph = []
                continue

            # Check if line is a heading
            heading_info = self._identify_heading(line)

            if heading_info:
                # End current paragraph if exists
                if current_paragraph:
                    paragraph_text = " ".join(current_paragraph)
                    elements.append(
                        {
                            "type": "paragraph",
                            "content": paragraph_text,
                            "line_start": line_num - len(current_paragraph),
                            "line_end": line_num - 1,
                            "level": 0,
                        }
                    )
                    current_paragraph = []

                # Add heading
                elements.append(
                    {
                        "type": "heading",
                        "content": line,
                        "line_start": line_num,
                        "line_end": line_num,
                        "level": heading_info["level"],
                        "pattern": heading_info["pattern"],
                    }
                )
            else:
                # Regular text line - add to current paragraph
                current_paragraph.append(line)

        # Handle final paragraph
        if current_paragraph:
            paragraph_text = " ".join(current_paragraph)
            elements.append(
                {
                    "type": "paragraph",
                    "content": paragraph_text,
                    "line_start": len(lines) - len(current_paragraph),
                    "line_end": len(lines) - 1,
                    "level": 0,
                }
            )

        return elements

    def _identify_heading(self, line: str) -> dict[str, Any] | None:
        """Identify if a line is a heading and determine its level."""
        for pattern_idx, pattern in enumerate(self.heading_patterns):
            if re.match(pattern, line, re.MULTILINE):
                # Determine heading level based on pattern
                level = 1  # Default level

                if pattern.startswith(r"^#{1,6}"):  # Markdown headings
                    level = len(line) - len(line.lstrip("#"))
                elif pattern.startswith(r"^\d+\."):  # Numbered sections
                    # Count dots to determine nesting level
                    level = line.count(".")
                elif pattern.startswith(r"^[IVX]+\."):  # Roman numerals
                    level = 1
                elif pattern.startswith(r"^[A-Z][A-Z\s]{2,}$"):  # ALL CAPS
                    level = 1  # Top level
                else:
                    level = 2  # Default for other patterns

                return {
                    "level": min(level, 6),  # Cap at level 6
                    "pattern": pattern,
                    "pattern_index": pattern_idx,
                }

        return None

    async def _create_structure_aware_chunks(
        self, elements: list[dict[str, Any]], full_text: str
    ) -> list[TextChunk]:
        """Create chunks while preserving document structure."""
        chunks = []
        current_chunk_elements = []
        current_chunk_tokens = 0
        chunk_index = 0

        i = 0
        while i < len(elements):
            element = elements[i]
            element_tokens = len(self.encoding.encode(element["content"]))

            # Check if adding this element would exceed max chunk size
            if (
                current_chunk_tokens + element_tokens > self.max_chunk_size
                and current_chunk_elements
            ):
                # Create chunk from current elements
                chunk = await self._create_chunk_from_elements(
                    current_chunk_elements, chunk_index, full_text
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start new chunk
                current_chunk_elements = []
                current_chunk_tokens = 0

            # Handle headings specially
            if element["type"] == "heading" and self.preserve_headings:
                # If we have content in current chunk, finish it first
                if current_chunk_elements and not self._last_element_is_heading(
                    current_chunk_elements
                ):
                    chunk = await self._create_chunk_from_elements(
                        current_chunk_elements, chunk_index, full_text
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_chunk_elements = []
                    current_chunk_tokens = 0

                # Add heading to new chunk
                current_chunk_elements.append(element)
                current_chunk_tokens += element_tokens

                # Try to add following content under this heading
                j = i + 1
                while j < len(elements):
                    next_element = elements[j]
                    next_tokens = len(self.encoding.encode(next_element["content"]))

                    # Stop if we hit another heading of same or higher level
                    if (
                        next_element["type"] == "heading"
                        and next_element["level"] <= element["level"]
                    ):
                        break

                    # Stop if adding would exceed chunk size
                    if current_chunk_tokens + next_tokens > self.max_chunk_size:
                        break

                    # Add element to current chunk
                    current_chunk_elements.append(next_element)
                    current_chunk_tokens += next_tokens
                    j += 1

                i = j  # Skip elements we've already processed
                continue

            # Handle paragraphs
            if element["type"] == "paragraph":
                if self.preserve_paragraphs and element_tokens > self.max_chunk_size:
                    # Split large paragraph by sentences
                    sentences = self._split_paragraph_into_sentences(element["content"])
                    for sentence in sentences:
                        sentence_tokens = len(self.encoding.encode(sentence))

                        if current_chunk_tokens + sentence_tokens > self.max_chunk_size:
                            if current_chunk_elements:
                                chunk = await self._create_chunk_from_elements(
                                    current_chunk_elements, chunk_index, full_text
                                )
                                chunks.append(chunk)
                                chunk_index += 1
                                current_chunk_elements = []
                                current_chunk_tokens = 0

                        # Add sentence as paragraph element
                        sentence_element = {
                            "type": "paragraph",
                            "content": sentence,
                            "line_start": element["line_start"],
                            "line_end": element["line_end"],
                            "level": 0,
                            "is_sentence_split": True,
                        }
                        current_chunk_elements.append(sentence_element)
                        current_chunk_tokens += sentence_tokens
                else:
                    # Add whole paragraph
                    current_chunk_elements.append(element)
                    current_chunk_tokens += element_tokens

            i += 1

        # Handle remaining elements
        if current_chunk_elements:
            chunk = await self._create_chunk_from_elements(
                current_chunk_elements, chunk_index, full_text
            )
            chunks.append(chunk)

        return chunks

    def _last_element_is_heading(self, elements: list[dict[str, Any]]) -> bool:
        """Check if the last element in the list is a heading."""
        return elements and elements[-1]["type"] == "heading"

    def _split_paragraph_into_sentences(self, paragraph: str) -> list[str]:
        """Split a paragraph into sentences."""
        # Simple sentence splitting
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        return [s.strip() for s in sentences if s.strip()]

    async def _create_chunk_from_elements(
        self, elements: list[dict[str, Any]], chunk_index: int, full_text: str
    ) -> TextChunk:
        """Create a TextChunk from structural elements."""
        # Combine element content
        content_parts = []
        for element in elements:
            if element["type"] == "heading":
                content_parts.append(element["content"])
            else:
                content_parts.append(element["content"])

        content = "\n\n".join(content_parts)
        token_count = len(self.encoding.encode(content))

        # Find character positions in full text
        first_element_content = elements[0]["content"]
        start_char = full_text.find(first_element_content)
        if start_char == -1:
            start_char = 0

        end_char = start_char + len(content)

        # Create metadata
        metadata = {
            "element_count": len(elements),
            "heading_count": sum(1 for elem in elements if elem["type"] == "heading"),
            "paragraph_count": sum(
                1 for elem in elements if elem["type"] == "paragraph"
            ),
            "structure_preserved": True,
        }

        # Add heading information if present
        headings = [elem for elem in elements if elem["type"] == "heading"]
        if headings:
            metadata["headings"] = [
                {"content": h["content"], "level": h["level"]} for h in headings
            ]
            metadata["primary_heading"] = headings[0]["content"]
            metadata["heading_level"] = headings[0]["level"]

        return self._create_chunk(
            content=content,
            chunk_index=chunk_index,
            start_char=start_char,
            end_char=end_char,
            token_count=token_count,
            metadata=metadata,
        )
