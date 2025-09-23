"""OCR-specific text cleaning utilities."""

import re
import time
from typing import Any

from .base import CleaningResult, TextCleaner


class OCRTextCleaner(TextCleaner):
    """Text cleaner specialized for OCR-extracted text."""

    def __init__(
        self,
        fix_common_ocr_errors: bool = True,
        remove_artifacts: bool = True,
        fix_spacing: bool = True,
        confidence_threshold: float = 0.8,
        remove_low_confidence: bool = False,
        **kwargs: Any,
    ):
        """Initialize OCR text cleaner.

        Args:
            fix_common_ocr_errors: Fix common OCR character recognition errors
            remove_artifacts: Remove OCR artifacts like random characters
            fix_spacing: Fix spacing issues common in OCR
            confidence_threshold: Confidence threshold for text filtering
            remove_low_confidence: Remove text below confidence threshold
        """
        super().__init__("ocr_cleaner", **kwargs)

        self.fix_common_ocr_errors = fix_common_ocr_errors
        self.remove_artifacts = remove_artifacts
        self.fix_spacing = fix_spacing
        self.confidence_threshold = confidence_threshold
        self.remove_low_confidence = remove_low_confidence

        # Common OCR character substitution errors
        self.ocr_corrections = {
            # Common character confusions
            "rn": "m",  # rn -> m
            "cl": "d",  # cl -> d
            "li": "h",  # li -> h (in some contexts)
            "0": "O",  # 0 -> O (in words)
            "1": "l",  # 1 -> l (in words)
            "5": "S",  # 5 -> S (in words)
            "8": "B",  # 8 -> B (in words)
            # Common punctuation errors
            ",,": ",",
            "..": ".",
            ";;": ";",
            "::": ":",
            # Spacing around punctuation
            " ,": ",",
            " .": ".",
            " ;": ";",
            " :": ":",
            "( ": "(",
            " )": ")",
        }

    async def clean(
        self, text: str, metadata: dict[str, Any] | None = None
    ) -> CleaningResult:
        """Clean OCR-extracted text."""
        start_time = time.time()
        original_text = text

        try:
            cleaning_steps = []

            # Step 1: Fix common OCR errors
            if self.fix_common_ocr_errors:
                text, step_info = self._fix_common_ocr_errors(text)
                cleaning_steps.append(step_info)

            # Step 2: Remove OCR artifacts
            if self.remove_artifacts:
                text, step_info = self._remove_ocr_artifacts(text)
                cleaning_steps.append(step_info)

            # Step 3: Fix spacing issues
            if self.fix_spacing:
                text, step_info = self._fix_spacing_issues(text)
                cleaning_steps.append(step_info)

            # Step 4: Remove low confidence text (if metadata available)
            if self.remove_low_confidence and metadata:
                text, step_info = self._remove_low_confidence_text(text, metadata)
                cleaning_steps.append(step_info)

            # Step 5: Final cleanup
            text, step_info = self._final_cleanup(text)
            cleaning_steps.append(step_info)

            processing_time = (time.time() - start_time) * 1000

            return self._create_result(
                success=True,
                cleaned_text=text,
                original_text=original_text,
                processing_time_ms=processing_time,
                cleaning_steps=cleaning_steps,
                total_steps=len(cleaning_steps),
                confidence_threshold=self.confidence_threshold,
            )

        except Exception as e:
            self.logger.error("ocr_cleaning_error", error=str(e))
            return self._create_result(
                success=False,
                error=f"OCR cleaning failed: {str(e)}",
                original_text=original_text,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _fix_common_ocr_errors(self, text: str) -> tuple[str, dict[str, Any]]:
        """Fix common OCR character recognition errors."""
        corrections_made = 0

        # Apply character-level corrections
        for wrong, correct in self.ocr_corrections.items():
            old_text = text
            text = text.replace(wrong, correct)
            if text != old_text:
                corrections_made += 1

        # Fix common word-level errors
        word_corrections = {
            r"\bthe\b": "the",  # Common OCR errors for "the"
            r"\bteh\b": "the",
            r"\btha\b": "the",
            r"\band\b": "and",  # Common OCR errors for "and"
            r"\badn\b": "and",
            r"\bnad\b": "and",
            r"\bwith\b": "with",  # Common OCR errors for "with"
            r"\bwlth\b": "with",
        }

        for pattern, replacement in word_corrections.items():
            old_text = text
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if text != old_text:
                corrections_made += 1

        return text, {
            "step": "fix_common_ocr_errors",
            "corrections_made": corrections_made,
            "character_corrections": len(self.ocr_corrections),
            "word_corrections": len(word_corrections),
        }

    def _remove_ocr_artifacts(self, text: str) -> tuple[str, dict[str, Any]]:
        """Remove OCR artifacts and noise."""
        original_length = len(text)

        # Remove isolated single characters that are likely artifacts
        text = re.sub(r"\b[a-zA-Z]\b(?!\s[a-zA-Z]\b)", "", text)

        # Remove sequences of random characters (likely OCR noise)
        # Pattern: 3+ characters with no vowels and unusual character combinations
        text = re.sub(r"\b[bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ]{3,}\b", "", text)

        # Remove excessive punctuation
        text = re.sub(r"[.]{4,}", "...", text)  # Multiple dots
        text = re.sub(r"[-]{3,}", "--", text)  # Multiple dashes
        text = re.sub(r"[_]{3,}", "", text)  # Multiple underscores

        # Remove standalone numbers that are likely page numbers or artifacts
        text = re.sub(r"\b\d{1,3}\b(?=\s|$)", "", text)

        artifacts_removed = original_length - len(text)

        return text, {
            "step": "remove_ocr_artifacts",
            "characters_removed": artifacts_removed,
            "artifact_patterns": 4,
        }

    def _fix_spacing_issues(self, text: str) -> tuple[str, dict[str, Any]]:
        """Fix spacing issues common in OCR text."""
        fixes_made = 0

        # Fix missing spaces after punctuation
        patterns = [
            (r"([.!?])([A-Z])", r"\1 \2"),  # Period followed by capital letter
            (
                r"([,;:])([a-zA-Z])",
                r"\1 \2",
            ),  # Comma/semicolon/colon followed by letter
            (
                r"([a-z])([A-Z])",
                r"\1 \2",
            ),  # Lowercase followed by uppercase (likely missing space)
        ]

        for pattern, replacement in patterns:
            old_text = text
            text = re.sub(pattern, replacement, text)
            if text != old_text:
                fixes_made += 1

        # Fix excessive spaces
        text = re.sub(r" {2,}", " ", text)

        # Fix spaces around punctuation (already in ocr_corrections but more comprehensive)
        spacing_fixes = [
            (r" +([,.!?;:])", r"\1"),  # Remove space before punctuation
            (r"([,.!?;:]) +", r"\1 "),  # Normalize space after punctuation
            (r"\( +", "("),  # Remove space after opening parenthesis
            (r" +\)", ")"),  # Remove space before closing parenthesis
        ]

        for pattern, replacement in spacing_fixes:
            old_text = text
            text = re.sub(pattern, replacement, text)
            if text != old_text:
                fixes_made += 1

        return text, {
            "step": "fix_spacing_issues",
            "fixes_made": fixes_made,
            "patterns_applied": len(patterns) + len(spacing_fixes),
        }

    def _remove_low_confidence_text(
        self, text: str, metadata: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Remove text with low OCR confidence scores."""
        # This would require confidence information from OCR metadata
        # For now, implement a basic version

        removed_chars = 0

        # If we have confidence data, use it
        if "confidence_scores" in metadata:
            # This would be implemented with actual confidence data
            pass
        else:
            # Heuristic: remove very short "words" that are likely low confidence
            original_length = len(text)
            text = re.sub(
                r"\b[a-zA-Z]{1,2}\b(?!\s(?:a|I|is|in|on|at|to|of|or|an|as|be|by|do|go|he|if|it|me|my|no|of|on|or|so|to|up|us|we)\b)",
                "",
                text,
            )
            removed_chars = original_length - len(text)

        return text, {
            "step": "remove_low_confidence_text",
            "characters_removed": removed_chars,
            "confidence_threshold": self.confidence_threshold,
            "has_confidence_data": (
                "confidence_scores" in metadata if metadata else False
            ),
        }

    def _final_cleanup(self, text: str) -> tuple[str, dict[str, Any]]:
        """Final cleanup pass."""
        original_length = len(text)

        # Remove multiple newlines
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Remove leading/trailing whitespace
        text = text.strip()

        # Remove empty lines
        lines = text.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]
        text = "\n".join(non_empty_lines)

        return text, {
            "step": "final_cleanup",
            "characters_removed": original_length - len(text),
            "final_length": len(text),
        }
