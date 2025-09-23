"""General text cleaning utilities."""

import re
import time
import unicodedata
from typing import Any

from .base import CleaningResult, TextCleaner


class GeneralTextCleaner(TextCleaner):
    """General-purpose text cleaner for various document types."""

    def __init__(
        self,
        normalize_unicode: bool = True,
        remove_control_chars: bool = True,
        fix_encoding_issues: bool = True,
        normalize_whitespace: bool = True,
        remove_urls: bool = False,
        remove_emails: bool = False,
        remove_phone_numbers: bool = False,
        preserve_structure: bool = True,
        **kwargs: Any,
    ):
        """Initialize general text cleaner.

        Args:
            normalize_unicode: Normalize Unicode characters
            remove_control_chars: Remove control characters
            fix_encoding_issues: Fix common encoding issues
            normalize_whitespace: Normalize whitespace
            remove_urls: Remove URLs from text
            remove_emails: Remove email addresses
            remove_phone_numbers: Remove phone numbers
            preserve_structure: Preserve paragraph and section structure
        """
        super().__init__("general_cleaner", **kwargs)

        self.normalize_unicode = normalize_unicode
        self.remove_control_chars = remove_control_chars
        self.fix_encoding_issues = fix_encoding_issues
        self.normalize_whitespace = normalize_whitespace
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_phone_numbers = remove_phone_numbers
        self.preserve_structure = preserve_structure

    async def clean(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> CleaningResult:
        """Clean text using general cleaning strategies."""
        start_time = time.time()
        original_text = text

        try:
            cleaning_steps = []

            # Step 1: Fix encoding issues
            if self.fix_encoding_issues:
                text, step_info = self._fix_encoding_issues(text)
                cleaning_steps.append(step_info)

            # Step 2: Normalize Unicode
            if self.normalize_unicode:
                text, step_info = self._normalize_unicode(text)
                cleaning_steps.append(step_info)

            # Step 3: Remove control characters
            if self.remove_control_chars:
                text, step_info = self._remove_control_characters(text)
                cleaning_steps.append(step_info)

            # Step 4: Remove PII if requested
            if self.remove_urls:
                text, step_info = self._remove_urls(text)
                cleaning_steps.append(step_info)

            if self.remove_emails:
                text, step_info = self._remove_emails(text)
                cleaning_steps.append(step_info)

            if self.remove_phone_numbers:
                text, step_info = self._remove_phone_numbers(text)
                cleaning_steps.append(step_info)

            # Step 5: Normalize whitespace (usually last)
            if self.normalize_whitespace:
                text, step_info = self._normalize_whitespace(text)
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
            self.logger.error("general_cleaning_error", error=str(e))
            return self._create_result(
                success=False,
                error=f"General cleaning failed: {str(e)}",
                original_text=original_text,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _fix_encoding_issues(self, text: str) -> tuple[str, dict[str, Any]]:
        """Fix common encoding issues."""
        fixes_made = 0

        # Common encoding issue replacements
        encoding_fixes = {
            # Smart quotes and dashes
            '"': '"',  # Left double quotation mark
            """: "'",  # Left single quotation mark
            """: "'",  # Right single quotation mark
            "–": "-",  # En dash
            "—": "--",  # Em dash
            "…": "...",  # Horizontal ellipsis
            # Common Windows-1252 issues
            "â€™": "'",  # Apostrophe
            "â€œ": '"',  # Left double quote
            "â€": '"',  # Right double quote
            'â€"': "--",  # Em dash
            "â€¢": "•",  # Bullet
            # Other common issues
            "Ã¡": "á",  # á with encoding issue
            "Ã©": "é",  # é with encoding issue
            "Ã­": "í",  # í with encoding issue
            "Ã³": "ó",  # ó with encoding issue
            "Ãº": "ú",  # ú with encoding issue
        }

        for wrong, correct in encoding_fixes.items():
            if wrong in text:
                text = text.replace(wrong, correct)
                fixes_made += 1

        return text, {
            "step": "fix_encoding_issues",
            "fixes_made": fixes_made,
            "patterns_checked": len(encoding_fixes),
        }

    def _normalize_unicode(self, text: str) -> tuple[str, dict[str, Any]]:
        """Normalize Unicode characters."""
        original_length = len(text)

        # Normalize to NFC (Canonical Decomposition, followed by Canonical Composition)
        normalized_text = unicodedata.normalize("NFC", text)

        # Remove or replace problematic Unicode categories
        cleaned_chars = []
        removed_count = 0

        for char in normalized_text:
            category = unicodedata.category(char)

            # Keep most characters, but handle special cases
            if category.startswith("C"):  # Control characters
                if char in "\n\r\t":  # Keep important whitespace
                    cleaned_chars.append(char)
                else:
                    removed_count += 1
            else:
                cleaned_chars.append(char)

        cleaned_text = "".join(cleaned_chars)

        return cleaned_text, {
            "step": "normalize_unicode",
            "original_length": original_length,
            "normalized_length": len(cleaned_text),
            "control_chars_removed": removed_count,
        }

    def _remove_control_characters(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove control characters except important whitespace."""
        original_length = len(text)

        # Remove control characters but keep \n, \r, \t
        cleaned_text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        removed_count = original_length - len(cleaned_text)

        return cleaned_text, {
            "step": "remove_control_characters",
            "characters_removed": removed_count,
        }

    def _remove_urls(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove URLs from text."""
        # URL pattern
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|www\.[^\s<>"{}|\\^`\[\]]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s<>"{}|\\^`\[\]]*'

        urls_found = len(re.findall(url_pattern, text))
        cleaned_text = re.sub(url_pattern, "[URL_REMOVED]", text)

        return cleaned_text, {"step": "remove_urls", "urls_removed": urls_found}

    def _remove_emails(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove email addresses from text."""
        # Email pattern
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

        emails_found = len(re.findall(email_pattern, text))
        cleaned_text = re.sub(email_pattern, "[EMAIL_REMOVED]", text)

        return cleaned_text, {"step": "remove_emails", "emails_removed": emails_found}

    def _remove_phone_numbers(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove phone numbers from text."""
        # Phone number patterns
        phone_patterns = [
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # US format
            r"\b\(\d{3}\)\s?\d{3}[-.]?\d{4}\b",  # (123) 456-7890
            r"\b\+\d{1,3}[-.\s]?\d{1,14}\b",  # International format
        ]

        phones_removed = 0
        for pattern in phone_patterns:
            phones_found = len(re.findall(pattern, text))
            text = re.sub(pattern, "[PHONE_REMOVED]", text)
            phones_removed += phones_found

        return text, {
            "step": "remove_phone_numbers",
            "phone_numbers_removed": phones_removed,
            "patterns_used": len(phone_patterns),
        }

    def _normalize_whitespace(self, text: str) -> tuple[str, dict[str, Any]]:
        """Normalize whitespace while preserving structure."""
        original_length = len(text)

        if self.preserve_structure:
            # Preserve paragraph breaks but normalize other whitespace
            paragraphs = text.split("\n\n")
            normalized_paragraphs = []

            for paragraph in paragraphs:
                # Normalize whitespace within paragraph
                normalized = re.sub(r"\s+", " ", paragraph.strip())
                if normalized:  # Only add non-empty paragraphs
                    normalized_paragraphs.append(normalized)

            cleaned_text = "\n\n".join(normalized_paragraphs)
        else:
            # Aggressive whitespace normalization
            cleaned_text = re.sub(r"\s+", " ", text).strip()

        return cleaned_text, {
            "step": "normalize_whitespace",
            "characters_removed": original_length - len(cleaned_text),
            "preserve_structure": self.preserve_structure,
            "final_length": len(cleaned_text),
        }
