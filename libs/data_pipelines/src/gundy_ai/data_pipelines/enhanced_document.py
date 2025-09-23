"""Enhanced document processor with multiple PDF parsers and fallback strategies."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import structlog

from .base import BaseProcessor, ProcessingResult, ProcessorConfig
from .document import DocumentMetadata, DocumentType, ProcessedDocument
from .parsers import (
    OCRFallbackParser,
    PDFParser,
    PDFParsingResult,
    PDFPlumberParser,
    PyMuPDFParser,
    PyPDFParser,
)
from .text_cleaning import (
    GeneralTextCleaner,
    OCRTextCleaner,
    PDFTextCleaner,
    TextCleaner,
)
from .audit_integration import ProcessingAuditHook

logger = structlog.get_logger(__name__)


class EnhancedDocumentProcessor(BaseProcessor[str, ProcessedDocument]):
    """Enhanced document processor with multiple PDF parsing strategies."""

    def __init__(
        self,
        config: ProcessorConfig,
        pdf_parser_priority: list[str] | None = None,
        enable_ocr_fallback: bool = True,
        ocr_confidence_threshold: float = 0.6,
        min_text_extraction_ratio: float = 0.1,
        enable_text_cleaning: bool = True,
        text_cleaning_strategy: str = "auto",
        audit_hook: Any | None = None,
        actor_id: str = "system",
        tenant_id: str = "default",
    ):
        """Initialize enhanced document processor.

        Args:
            config: Processor configuration
            pdf_parser_priority: List of parser names in priority order
            enable_ocr_fallback: Whether to use OCR as fallback
            ocr_confidence_threshold: Minimum OCR confidence threshold
            min_text_extraction_ratio: Minimum ratio of extracted text to trigger fallback
            enable_text_cleaning: Whether to apply text cleaning
            text_cleaning_strategy: Text cleaning strategy ("auto", "pdf", "ocr", "general")
            audit_hook: Optional audit hook for tracking operations
            actor_id: ID of the actor performing the operation
            tenant_id: Tenant identifier for multi-tenant systems
        """
        super().__init__(config)

        # Default parser priority: best quality first, fastest last
        self.pdf_parser_priority = pdf_parser_priority or [
            "pdfplumber",  # Best for layout preservation
            "pymupdf",  # Fast and feature-rich
            "pypdf",  # Lightweight fallback
        ]

        self.enable_ocr_fallback = enable_ocr_fallback
        self.ocr_confidence_threshold = ocr_confidence_threshold
        self.min_text_extraction_ratio = min_text_extraction_ratio
        self.enable_text_cleaning = enable_text_cleaning
        self.text_cleaning_strategy = text_cleaning_strategy
        self.actor_id = actor_id
        self.tenant_id = tenant_id

        # Initialize audit hook
        self.audit_hook = ProcessingAuditHook(audit_hook)

        # Initialize parsers
        self.parsers: dict[str, PDFParser] = {
            "pdfplumber": PDFPlumberParser(extract_tables=True, preserve_layout=True),
            "pymupdf": PyMuPDFParser(
                extract_images=False, extract_links=False, preserve_formatting=True
            ),
            "pypdf": PyPDFParser(),
            "ocr_fallback": OCRFallbackParser(
                confidence_threshold=ocr_confidence_threshold
            ),
        }

        # Initialize text cleaners
        self.text_cleaners: dict[str, TextCleaner] = {
            "pdf": PDFTextCleaner(),
            "ocr": OCRTextCleaner(confidence_threshold=ocr_confidence_threshold),
            "general": GeneralTextCleaner(),
        }

    def validate_input(self, input_data: str) -> bool:
        """Validate input is a valid file path."""
        if not isinstance(input_data, str):
            return False
        path = Path(input_data)
        return path.exists() and path.is_file()

    async def process(self, file_path: str) -> ProcessingResult[ProcessedDocument]:
        """Process a document with enhanced PDF parsing."""
        try:
            path = Path(file_path)
            document_type = self._detect_document_type(path)

            if document_type == DocumentType.PDF:
                return await self._process_pdf(path)
            else:
                # Use original processing for non-PDF files
                return await self._process_non_pdf(path, document_type)

        except Exception as e:
            self.logger.error(
                "enhanced_document.processing.error", error=str(e), file_path=file_path
            )
            return ProcessingResult(
                success=False, error=f"Failed to process document: {str(e)}"
            )

    async def _process_pdf(self, path: Path) -> ProcessingResult[ProcessedDocument]:
        """Process PDF with multiple parser strategies."""
        # Start audit logging
        event_id = await self.audit_hook.log_processing_start(
            str(path),
            actor_id=self.actor_id,
            tenant_id=self.tenant_id,
            document_type="pdf",
            processing_strategy="enhanced_pdf",
        )

        start_time = time.time()
        parsing_attempts = []
        best_result: PDFParsingResult | None = None

        # Try parsers in priority order
        for parser_name in self.pdf_parser_priority:
            if parser_name not in self.parsers:
                continue

            parser = self.parsers[parser_name]

            try:
                if not parser.can_handle(path):
                    self.logger.debug(
                        "parser_cannot_handle", parser=parser_name, file_path=str(path)
                    )
                    continue

                self.logger.info(
                    "attempting_pdf_parse", parser=parser_name, file_path=str(path)
                )

                result = await parser.parse(path)
                parsing_attempts.append(
                    {
                        "parser": parser_name,
                        "success": result.success,
                        "error": result.error,
                        "processing_time_ms": result.processing_time_ms,
                        "text_length": (
                            result.total_text_length if result.success else 0
                        ),
                    }
                )

                # Log parsing attempt
                await self.audit_hook.log_parsing_attempt(
                    event_id=event_id,
                    parser_name=parser_name,
                    success=result.success,
                    processing_time_ms=result.processing_time_ms,
                    text_length=result.total_text_length if result.success else 0,
                    error_message=result.error,
                )

                if result.success:
                    # Check if extraction quality is acceptable
                    if self._is_extraction_quality_acceptable(result, path):
                        best_result = result
                        break
                    else:
                        self.logger.warning(
                            "low_quality_extraction",
                            parser=parser_name,
                            text_length=result.total_text_length,
                            file_path=str(path),
                        )
                        # Keep this result but try other parsers
                        if (
                            best_result is None
                            or result.total_text_length > best_result.total_text_length
                        ):
                            best_result = result

            except Exception as e:
                self.logger.warning(
                    "parser_failed",
                    parser=parser_name,
                    error=str(e),
                    file_path=str(path),
                )
                parsing_attempts.append(
                    {
                        "parser": parser_name,
                        "success": False,
                        "error": str(e),
                        "processing_time_ms": 0,
                        "text_length": 0,
                    }
                )

        # Try OCR fallback if enabled and needed
        if self.enable_ocr_fallback and (
            best_result is None
            or not self._is_extraction_quality_acceptable(best_result, path)
        ):
            try:
                self.logger.info("attempting_ocr_fallback", file_path=str(path))
                ocr_parser = self.parsers["ocr_fallback"]
                ocr_result = await ocr_parser.parse(path)

                parsing_attempts.append(
                    {
                        "parser": "ocr_fallback",
                        "success": ocr_result.success,
                        "error": ocr_result.error,
                        "processing_time_ms": ocr_result.processing_time_ms,
                        "text_length": (
                            ocr_result.total_text_length if ocr_result.success else 0
                        ),
                    }
                )

                if ocr_result.success:
                    # Use OCR result if it's better or if no other result exists
                    if (
                        best_result is None
                        or ocr_result.total_text_length > best_result.total_text_length
                    ):
                        best_result = ocr_result

            except Exception as e:
                self.logger.warning(
                    "ocr_fallback_failed", error=str(e), file_path=str(path)
                )
                parsing_attempts.append(
                    {
                        "parser": "ocr_fallback",
                        "success": False,
                        "error": str(e),
                        "processing_time_ms": 0,
                        "text_length": 0,
                    }
                )

        # Return best result or failure
        if best_result and best_result.success:
            result = await self._convert_pdf_result_to_processed_document(
                best_result, path, parsing_attempts, event_id
            )

            # Log successful processing
            if result.success:
                doc = result.data
                await self.audit_hook.log_processing_success(
                    event_id=event_id,
                    processing_time_ms=(time.time() - start_time) * 1000,
                    text_length=len(doc.full_text),
                    word_count=doc.metadata.word_count or 0,
                    parser_used=best_result.parser_used,
                    text_cleaning_enabled=self.enable_text_cleaning,
                    ocr_used=best_result.ocr_used,
                )

            return result
        else:
            # Log processing failure
            processing_time = (time.time() - start_time) * 1000
            await self.audit_hook.log_processing_failure(
                event_id=event_id,
                error_message="All PDF parsing strategies failed",
                processing_time_ms=processing_time,
                parsing_attempts=parsing_attempts,
            )

            return ProcessingResult(
                success=False,
                error="All PDF parsing strategies failed",
                metadata={"parsing_attempts": parsing_attempts},
            )

    def _is_extraction_quality_acceptable(
        self, result: PDFParsingResult, path: Path
    ) -> bool:
        """Check if extraction quality meets minimum standards."""
        if not result.success:
            return False

        # Check minimum text length ratio
        file_size = path.stat().st_size
        text_length = result.total_text_length

        # Rough heuristic: expect at least some text per KB of file
        expected_min_chars = file_size * self.min_text_extraction_ratio / 1024

        return text_length >= expected_min_chars

    async def _convert_pdf_result_to_processed_document(
        self,
        pdf_result: PDFParsingResult,
        path: Path,
        parsing_attempts: list[dict[str, Any]],
        event_id: str,
    ) -> ProcessingResult[ProcessedDocument]:
        """Convert PDF parsing result to ProcessedDocument."""

        # Combine text from all pages
        full_text = pdf_result.get_full_text()

        # Apply text cleaning if enabled
        cleaning_result = None
        if self.enable_text_cleaning and full_text:
            original_length = len(full_text)
            cleaning_result = await self._clean_text(full_text, pdf_result)
            if cleaning_result.success:
                full_text = cleaning_result.cleaned_text

                # Log text cleaning operation
                await self.audit_hook.log_text_cleaning(
                    event_id=event_id,
                    cleaning_strategy=self.text_cleaning_strategy,
                    original_length=original_length,
                    cleaned_length=len(full_text),
                    processing_time_ms=cleaning_result.processing_time_ms,
                    cleaning_steps=cleaning_result.metadata.get("cleaning_steps", []),
                )

        # Create metadata
        metadata = DocumentMetadata(
            filename=path.name,
            document_type=DocumentType.PDF,
            size_bytes=path.stat().st_size,
            page_count=pdf_result.page_count,
            word_count=len(full_text.split()) if full_text else 0,
            custom_metadata={
                "file_path": str(path),
                "file_extension": path.suffix,
                "parser_used": pdf_result.parser_used,
                "ocr_used": pdf_result.ocr_used,
                "processing_time_ms": pdf_result.processing_time_ms,
                "parsing_attempts": parsing_attempts,
                "text_cleaning_enabled": self.enable_text_cleaning,
                "text_cleaning_strategy": self.text_cleaning_strategy,
                "event_id": event_id,  # Include event ID for downstream processors
                **(cleaning_result.metadata if cleaning_result else {}),
                **pdf_result.metadata,
            },
        )

        # Create processed document (chunks will be added by chunking processor)
        processed_doc = ProcessedDocument(
            metadata=metadata, chunks=[], full_text=full_text
        )

        return ProcessingResult(
            success=True,
            data=processed_doc,
            metadata={
                "document_type": DocumentType.PDF.value,
                "text_length": len(full_text),
                "word_count": metadata.word_count,
                "page_count": pdf_result.page_count,
                "parser_used": pdf_result.parser_used,
                "ocr_used": pdf_result.ocr_used,
                "processing_time_ms": pdf_result.processing_time_ms,
            },
        )

    async def _process_non_pdf(
        self, path: Path, document_type: DocumentType
    ) -> ProcessingResult[ProcessedDocument]:
        """Process non-PDF documents using original logic."""
        # Import here to avoid circular imports
        from .document import DocumentProcessor

        # Create a basic document processor for non-PDF files
        basic_processor = DocumentProcessor(self.config)
        return await basic_processor.process(str(path))

    async def _clean_text(self, text: str, pdf_result: PDFParsingResult) -> Any:
        """Clean extracted text using appropriate strategy."""
        # Determine cleaning strategy
        strategy = self.text_cleaning_strategy

        if strategy == "auto":
            # Auto-select based on parsing result
            if pdf_result.ocr_used:
                strategy = "ocr"
            else:
                strategy = "pdf"

        # Get appropriate cleaner
        if strategy in self.text_cleaners:
            cleaner = self.text_cleaners[strategy]
        else:
            # Fallback to general cleaner
            cleaner = self.text_cleaners["general"]

        # Clean the text
        return await cleaner.clean(text, pdf_result.metadata)

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
