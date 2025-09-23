"""PDF-specific text cleaning utilities."""

import re
import time
from typing import Any

from .base import CleaningResult, TextCleaner


class PDFTextCleaner(TextCleaner):
    """Text cleaner specialized for PDF-extracted text."""

    def __init__(
        self,
        remove_headers_footers: bool = True,
        remove_page_numbers: bool = True,
        fix_line_breaks: bool = True,
        remove_excessive_whitespace: bool = True,
        fix_hyphenation: bool = True,
        remove_watermarks: bool = True,
        header_footer_threshold: int = 3,
        **kwargs: Any,
    ):
        """Initialize PDF text cleaner.

        Args:
            remove_headers_footers: Remove repeated headers/footers
            remove_page_numbers: Remove page numbers
            fix_line_breaks: Fix broken line breaks in middle of sentences
            remove_excessive_whitespace: Remove extra spaces and empty lines
            fix_hyphenation: Fix hyphenated words split across lines
            remove_watermarks: Remove common watermark patterns
            header_footer_threshold: Minimum repetitions to consider header/footer
        """
        super().__init__("pdf_cleaner", **kwargs)

        self.remove_headers_footers = remove_headers_footers
        self.remove_page_numbers = remove_page_numbers
        self.fix_line_breaks = fix_line_breaks
        self.remove_excessive_whitespace = remove_excessive_whitespace
        self.fix_hyphenation = fix_hyphenation
        self.remove_watermarks = remove_watermarks
        self.header_footer_threshold = header_footer_threshold

    async def clean(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> CleaningResult:
        """Clean PDF-extracted text."""
        start_time = time.time()
        original_text = text

        try:
            cleaning_steps = []

            # Step 1: Remove headers and footers
            if self.remove_headers_footers:
                text, step_info = self._remove_headers_footers(text)
                cleaning_steps.append(step_info)

            # Step 2: Remove page numbers
            if self.remove_page_numbers:
                text, step_info = self._remove_page_numbers(text)
                cleaning_steps.append(step_info)

            # Step 3: Fix hyphenation
            if self.fix_hyphenation:
                text, step_info = self._fix_hyphenation(text)
                cleaning_steps.append(step_info)

            # Step 4: Fix line breaks
            if self.fix_line_breaks:
                text, step_info = self._fix_line_breaks(text)
                cleaning_steps.append(step_info)

            # Step 5: Remove watermarks
            if self.remove_watermarks:
                text, step_info = self._remove_watermarks(text)
                cleaning_steps.append(step_info)

            # Step 6: Remove excessive whitespace (always last)
            if self.remove_excessive_whitespace:
                text, step_info = self._remove_excessive_whitespace(text)
                cleaning_steps.append(step_info)

            processing_time = (time.time() - start_time) * 1000

            return self._create_result(
                success=True,
                cleaned_text=text,
                original_text=original_text,
                processing_time_ms=processing_time,
                cleaning_steps=cleaning_steps,
                total_steps=len(cleaning_steps),
            )

        except Exception as e:
            self.logger.error("pdf_cleaning_error", error=str(e))
            return self._create_result(
                success=False,
                error=f"PDF cleaning failed: {str(e)}",
                original_text=original_text,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _remove_headers_footers(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove repeated headers and footers."""
        lines = text.split("\n")
        line_counts = {}

        # Count occurrences of each line
        for line in lines:
            stripped = line.strip()
            if stripped and len(stripped) > 5:  # Ignore very short lines
                line_counts[stripped] = line_counts.get(stripped, 0) + 1

        # Find lines that appear frequently (likely headers/footers)
        repeated_lines = {
            line
            for line, count in line_counts.items()
            if count >= self.header_footer_threshold
        }

        # Remove repeated lines
        cleaned_lines = []
        removed_count = 0

        for line in lines:
            stripped = line.strip()
            if stripped in repeated_lines:
                removed_count += 1
            else:
                cleaned_lines.append(line)

        cleaned_text = "\n".join(cleaned_lines)

        return cleaned_text, {
            "step": "remove_headers_footers",
            "repeated_lines_found": len(repeated_lines),
            "lines_removed": removed_count,
            "threshold": self.header_footer_threshold,
        }

    def _remove_page_numbers(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove page numbers."""

        # Common page number patterns
        patterns = [
            r"^\s*\d+\s*$",  # Standalone numbers
            r"^\s*Page\s+\d+\s*$",  # "Page N"
            r"^\s*\d+\s*/\s*\d+\s*$",  # "N/M" format
            r"^\s*-\s*\d+\s*-\s*$",  # "-N-" format
            r"^\s*\|\s*\d+\s*\|\s*$",  # "|N|" format
        ]

        lines = text.split("\n")
        cleaned_lines = []
        removed_count = 0

        for line in lines:
            is_page_number = False
            for pattern in patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    is_page_number = True
                    removed_count += 1
                    break

            if not is_page_number:
                cleaned_lines.append(line)

        cleaned_text = "\n".join(cleaned_lines)

        return cleaned_text, {
            "step": "remove_page_numbers",
            "lines_removed": removed_count,
            "patterns_used": len(patterns),
        }

    def _fix_hyphenation(self, text: str) -> tuple[str, dict[str, Any]]:
        """Fix hyphenated words split across lines."""
        original_length = len(text)

        # Pattern for hyphenated words at end of line
        # Matches: word- \n word
        pattern = r"(\w+)-\s*\n\s*(\w+)"

        def replace_hyphen(match):
            return match.group(1) + match.group(2)

        cleaned_text = re.sub(pattern, replace_hyphen, text)
        fixes_made = len(re.findall(pattern, text))

        return cleaned_text, {
            "step": "fix_hyphenation",
            "hyphenations_fixed": fixes_made,
            "characters_saved": original_length - len(cleaned_text),
        }

    def _fix_line_breaks(self, text: str) -> tuple[str, dict[str, Any]]:
        """Fix broken line breaks in middle of sentences."""
        original_length = len(text)

        # Pattern for line breaks in middle of sentences
        # Look for lowercase letter followed by newline and lowercase letter
        pattern = r"([a-z,])\s*\n\s*([a-z])"

        def replace_break(match):
            return match.group(1) + " " + match.group(2)

        cleaned_text = re.sub(pattern, replace_break, text)
        fixes_made = len(re.findall(pattern, text))

        return cleaned_text, {
            "step": "fix_line_breaks",
            "line_breaks_fixed": fixes_made,
            "character_difference": len(cleaned_text) - original_length,
        }

    def _remove_watermarks(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove common watermark patterns."""

        # Common watermark patterns
        watermark_patterns = [
            r"CONFIDENTIAL",
            r"DRAFT",
            r"INTERNAL USE ONLY",
            r"PROPRIETARY",
            r"DO NOT DISTRIBUTE",
            r"PRELIMINARY",
            r"UNCONTROLLED COPY",
            r"FOR REVIEW ONLY",
        ]

        removed_count = 0
        for pattern in watermark_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            removed_count += matches

        return text, {
            "step": "remove_watermarks",
            "watermarks_removed": removed_count,
            "patterns_checked": len(watermark_patterns),
        }

    def _remove_excessive_whitespace(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove excessive whitespace and empty lines."""
        original_length = len(text)

        # Remove multiple spaces
        text = re.sub(r" +", " ", text)

        # Remove multiple newlines (keep max 2 for paragraph breaks)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove trailing/leading whitespace from lines
        lines = text.split("\n")
        cleaned_lines = [line.strip() for line in lines]

        # Remove empty lines at start and end
        while cleaned_lines and not cleaned_lines[0]:
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()

        cleaned_text = "\n".join(cleaned_lines)

        return cleaned_text, {
            "step": "remove_excessive_whitespace",
            "characters_removed": original_length - len(cleaned_text),
            "compression_ratio": (
                (original_length - len(cleaned_text)) / original_length
                if original_length > 0
                else 0
            ),
        }
