"""Example demonstrating OCR and image processing capabilities."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.data_pipelines import (
    EnhancedDocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
    OutputManager,
    OutputFormat,
)


async def main():
    """Demonstrate OCR and image processing capabilities."""
    print("🖼️  OCR and Image Processing Demo")
    print("=" * 50)

    # Initialize components with OCR-optimized settings
    print("🔧 Initializing OCR-enabled document processor...")

    doc_config = ProcessorConfig(name="ocr_demo")
    doc_processor = EnhancedDocumentProcessor(
        config=doc_config,
        # Prioritize OCR-capable parsers
        pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf", "ocr_fallback"],
        enable_ocr_fallback=True,
        ocr_confidence_threshold=0.6,  # Lower threshold for better recall
        min_text_extraction_ratio=0.05,  # Lower ratio to trigger OCR more easily
        enable_text_cleaning=True,
        text_cleaning_strategy="auto",  # Will use OCR cleaning for OCR-extracted text
    )

    chunker_config = ProcessorConfig(name="ocr_chunker")
    chunker = EnhancedTextChunker(
        config=chunker_config,
        strategy="structure_aware",  # Good for documents with varied layouts
        chunk_size=400,
        overlap=50,
    )

    output_manager = OutputManager()

    print("✅ Components initialized with OCR support")
    print()

    # Create sample documents that would benefit from OCR
    sample_documents = [
        {
            "name": "text_document.txt",
            "content": """
# Regular Text Document

This is a regular text document that doesn't need OCR processing.
It contains normal text that can be processed directly.

## Section 1
Regular text processing will handle this efficiently.

## Section 2
No images or scanned content here.
            """.strip(),
            "description": "Regular text document (no OCR needed)",
        },
        {
            "name": "mixed_content.txt",
            "content": """
# Mixed Content Document

This document simulates content that might come from a PDF with both text and images.

## Text Section
This part contains regular text that was extracted normally.

## Image Description Section
[This section would typically contain text extracted via OCR from images]

The following text simulates OCR-extracted content with typical artifacts:
- Sorne text with OCR errors (Some -> Sorne)
- Misrecognized characters: 0CR instead of OCR
- Spacing issues:word boundaries not detected
- Mixed case: TeXt ExTrAcTiOn

## Data Table (OCR Extracted)
Product    | Price  | Stock
-----------|--------|-------
Widget A   | $19.99 | 150
Widget B   | $24.99 | 75
Widget C   | $14.99 | 200

Note: This table was extracted from an image using OCR technology.
            """.strip(),
            "description": "Mixed content with simulated OCR artifacts",
        },
    ]

    print("📄 Processing Documents with OCR Pipeline...")
    print()

    processed_docs = []

    for i, doc_info in enumerate(sample_documents):
        print(f"🔄 Processing: {doc_info['name']}")
        print(f"   Description: {doc_info['description']}")

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(doc_info["content"])
            temp_file = f.name

        try:
            # Process document
            doc_result = await doc_processor.process(temp_file)

            if doc_result.success:
                document = doc_result.data

                print("   ✅ Success!")
                print(f"      📊 Text length: {len(document.full_text):,} characters")
                print(f"      📄 Word count: {document.metadata.word_count or 0}")

                # Check processing metadata for OCR usage
                metadata = document.metadata.custom_metadata
                ocr_used = metadata.get("ocr_used", False)
                parser_used = metadata.get("parser_used", "unknown")
                text_cleaning = metadata.get("text_cleaning_enabled", False)

                print(f"      🔧 Parser used: {parser_used}")
                print(f"      👁️  OCR used: {'Yes' if ocr_used else 'No'}")
                print(f"      🧹 Text cleaning: {'Yes' if text_cleaning else 'No'}")

                # Show parsing attempts if available
                attempts = metadata.get("parsing_attempts", [])
                if attempts:
                    print("      🔄 Parsing attempts:")
                    for attempt in attempts:
                        status = "✅" if attempt["success"] else "❌"
                        print(
                            f"         {status} {attempt['parser']}: {attempt.get('text_length', 0)} chars"
                        )

                # Chunk the document
                chunk_result = await chunker.process(document)
                if chunk_result.success:
                    chunked_doc = chunk_result.data
                    print(f"      ✂️  Chunks created: {len(chunked_doc.chunks)}")

                    # Show sample chunks
                    if chunked_doc.chunks:
                        print("      📝 Sample chunk:")
                        sample_chunk = chunked_doc.chunks[0]
                        preview = (
                            sample_chunk.content[:150] + "..."
                            if len(sample_chunk.content) > 150
                            else sample_chunk.content
                        )
                        print(f"         {repr(preview)}")

                    processed_docs.append(chunked_doc)
                else:
                    print(f"      ❌ Chunking failed: {chunk_result.error}")
            else:
                print(f"   ❌ Processing failed: {doc_result.error}")

        finally:
            # Cleanup
            Path(temp_file).unlink(missing_ok=True)

        print()

    # Demonstrate OCR-specific text cleaning
    print("🧹 OCR Text Cleaning Demo:")
    print()

    # Sample text with OCR artifacts
    ocr_text = """
    Sorne cornrnon 0CR errors include:
    - Character substitution: rn -> m, cl -> d
    - Spacing issues:word boundaries
    - Mixed case: TeXt ExTrAcTiOn
    - Number confusion: 0 (zero) vs O (letter)
    - Special characters: @pple instead of Apple
    
    This text contains typical OCR artifacts that need cleaning.
    """

    print("Original OCR text:")
    print(repr(ocr_text))
    print()

    # Create a temporary document to demonstrate OCR cleaning
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(ocr_text)
        temp_ocr_file = f.name

    try:
        # Process with OCR cleaning enabled
        ocr_processor = EnhancedDocumentProcessor(
            config=ProcessorConfig(name="ocr_cleaning_demo"),
            enable_text_cleaning=True,
            text_cleaning_strategy="ocr",  # Force OCR cleaning
        )

        ocr_result = await ocr_processor.process(temp_ocr_file)

        if ocr_result.success:
            cleaned_doc = ocr_result.data
            print("Cleaned text:")
            print(repr(cleaned_doc.full_text))
            print()

            # Show cleaning metadata
            cleaning_metadata = cleaned_doc.metadata.custom_metadata
            if "text_cleaning_enabled" in cleaning_metadata:
                print("🧹 Text cleaning details:")
                print(
                    f"   Strategy used: {cleaning_metadata.get('text_cleaning_strategy', 'unknown')}"
                )
                print(f"   Original length: {len(ocr_text)} chars")
                print(f"   Cleaned length: {len(cleaned_doc.full_text)} chars")
                reduction = len(ocr_text) - len(cleaned_doc.full_text)
                print(f"   Characters cleaned: {reduction}")

    finally:
        Path(temp_ocr_file).unlink(missing_ok=True)

    print()

    # Export processed documents in multiple formats
    if processed_docs:
        print("💾 Exporting Processed Documents...")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Export in multiple formats
            export_results = await output_manager.write_multiple_formats(
                documents=processed_docs,
                output_directory=temp_dir,
                formats=[OutputFormat.JSON, OutputFormat.NDJSON, OutputFormat.PARQUET],
                base_filename="ocr_processed_docs",
            )

            print("   Export results:")
            for format_type, result in export_results.items():
                if result.success:
                    size_kb = result.file_size / 1024
                    print(f"      ✅ {format_type.value}: {size_kb:.1f} KB")
                else:
                    print(f"      ❌ {format_type.value}: {result.error}")

    print()
    print("🎯 OCR Integration Benefits:")
    print("   • Automatic OCR fallback for scanned documents")
    print("   • Multiple parser strategies with quality assessment")
    print("   • OCR-specific text cleaning for better quality")
    print("   • Confidence thresholds for reliable extraction")
    print("   • Support for multiple languages")
    print("   • Image preprocessing for better OCR results")
    print()

    print("🔧 Configuration Options:")
    print("   • language: Tesseract language code ('eng', 'spa', 'fra', etc.)")
    print("   • dpi: Image resolution for OCR (higher = better quality)")
    print("   • confidence_threshold: Minimum OCR confidence (0.0-1.0)")
    print("   • preprocess_images: Enable image enhancement")
    print("   • ocr_confidence_threshold: Global OCR trigger threshold")
    print("   • min_text_extraction_ratio: Ratio to trigger OCR fallback")
    print()

    print("📋 Supported File Types:")
    print("   • PDF files (including scanned PDFs)")
    print("   • Image files (PNG, JPEG, TIFF) - via PDF conversion")
    print("   • Mixed content documents")
    print("   • Multi-language documents")
    print()

    print("🚀 Production Usage Tips:")
    print("   1. Set appropriate confidence thresholds for your use case")
    print("   2. Use language-specific models for better accuracy")
    print("   3. Enable text cleaning for OCR-extracted content")
    print("   4. Monitor OCR usage via audit logs and metrics")
    print("   5. Consider preprocessing images for better results")
    print("   6. Use structure-aware chunking for complex layouts")


async def demonstrate_advanced_ocr_config():
    """Demonstrate advanced OCR configuration options."""
    print("\n" + "=" * 60)
    print("🔬 Advanced OCR Configuration Demo")
    print("=" * 60)

    # Example configurations for different use cases
    configs = [
        {
            "name": "High Accuracy (Slow)",
            "config": {
                "pdf_parser_priority": ["ocr_fallback"],  # Force OCR
                "enable_ocr_fallback": True,
                "ocr_confidence_threshold": 0.8,  # High confidence
                "min_text_extraction_ratio": 0.0,  # Always use OCR
                "enable_text_cleaning": True,
                "text_cleaning_strategy": "ocr",
            },
            "use_case": "Critical documents requiring high accuracy",
        },
        {
            "name": "Balanced (Recommended)",
            "config": {
                "pdf_parser_priority": ["pymupdf", "pdfplumber", "ocr_fallback"],
                "enable_ocr_fallback": True,
                "ocr_confidence_threshold": 0.6,
                "min_text_extraction_ratio": 0.1,
                "enable_text_cleaning": True,
                "text_cleaning_strategy": "auto",
            },
            "use_case": "General purpose document processing",
        },
        {
            "name": "Fast Processing",
            "config": {
                "pdf_parser_priority": ["pymupdf", "pdfplumber"],
                "enable_ocr_fallback": False,  # Disable OCR for speed
                "enable_text_cleaning": True,
                "text_cleaning_strategy": "pdf",
            },
            "use_case": "High-volume processing where speed is critical",
        },
    ]

    for config_info in configs:
        print(f"\n📋 {config_info['name']}:")
        print(f"   Use case: {config_info['use_case']}")
        print("   Configuration:")
        for key, value in config_info["config"].items():
            print(f"      {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(demonstrate_advanced_ocr_config())
