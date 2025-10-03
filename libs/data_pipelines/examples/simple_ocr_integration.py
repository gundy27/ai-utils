"""Simple example showing OCR integration in data processing pipeline."""

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


async def process_documents_with_ocr(file_paths: list[str]):
    """Process documents with automatic OCR fallback."""

    print("🔧 Setting up OCR-enabled pipeline...")

    # 1. Initialize document processor with OCR support
    processor = EnhancedDocumentProcessor(
        config=ProcessorConfig(name="ocr_pipeline"),
        # OCR Configuration
        enable_ocr_fallback=True,  # Enable OCR as fallback
        ocr_confidence_threshold=0.6,  # Minimum OCR confidence (0.0-1.0)
        min_text_extraction_ratio=0.1,  # Trigger OCR if <10% text extracted
        # Parser priority (OCR is automatic fallback)
        pdf_parser_priority=[
            "pymupdf",  # Fast, good for text PDFs
            "pdfplumber",  # Good for tables and layout
            "ocr_fallback",  # OCR for scanned documents
        ],
        # Text cleaning (important for OCR)
        enable_text_cleaning=True,
        text_cleaning_strategy="auto",  # Auto-detects OCR text and cleans appropriately
    )

    # 2. Initialize chunker for processed text
    chunker = EnhancedTextChunker(
        config=ProcessorConfig(name="ocr_chunker"),
        strategy="structure_aware",  # Good for documents with varied layouts
        chunk_size=500,
        overlap=50,
    )

    # 3. Initialize output manager
    output_manager = OutputManager()

    print("✅ Pipeline initialized with OCR support")
    print()

    processed_documents = []

    # Process each document
    for file_path in file_paths:
        print(f"📄 Processing: {Path(file_path).name}")

        try:
            # Step 1: Extract text (with automatic OCR fallback)
            doc_result = await processor.process(file_path)

            if not doc_result.success:
                print(f"   ❌ Failed: {doc_result.error}")
                continue

            document = doc_result.data

            # Check processing details
            metadata = document.metadata.custom_metadata
            ocr_used = metadata.get("ocr_used", False)
            parser_used = metadata.get("parser_used", "unknown")
            text_length = len(document.full_text)

            print(f"   ✅ Extracted {text_length:,} characters")
            print(f"   🔧 Parser: {parser_used}")
            print(f"   👁️  OCR used: {'Yes' if ocr_used else 'No'}")

            # Step 2: Chunk the text
            chunk_result = await chunker.process(document)

            if chunk_result.success:
                chunked_doc = chunk_result.data
                print(f"   ✂️  Created {len(chunked_doc.chunks)} chunks")
                processed_documents.append(chunked_doc)
            else:
                print(f"   ❌ Chunking failed: {chunk_result.error}")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")

        print()

    # Step 3: Export results
    if processed_documents:
        print("💾 Exporting results...")

        with tempfile.TemporaryDirectory() as temp_dir:
            # Export in JSON format (human-readable)
            json_result = await output_manager.write_documents(
                processed_documents,
                Path(temp_dir) / "processed_documents.json",
                OutputFormat.JSON,
            )

            if json_result.success:
                size_kb = json_result.file_size / 1024
                print(f"   ✅ JSON export: {size_kb:.1f} KB")
                print(f"   📁 Location: {json_result.output_path}")

            # Also export as NDJSON for streaming/big data use
            ndjson_result = await output_manager.write_documents(
                processed_documents,
                Path(temp_dir) / "processed_documents.ndjson",
                OutputFormat.NDJSON,
                chunk_per_line=True,  # Each chunk as separate line
            )

            if ndjson_result.success:
                lines = ndjson_result.metadata.get("lines_written", 0)
                print(f"   ✅ NDJSON export: {lines} lines")

    return processed_documents


async def main():
    """Main demo function."""
    print("🖼️  Simple OCR Integration Demo")
    print("=" * 40)
    print()

    # Create sample documents for testing
    sample_docs = []

    # 1. Regular text document
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(
            """
# Sample Document

This is a regular text document that doesn't need OCR.
It contains normal, machine-readable text.

## Key Points
- Fast processing
- No OCR required
- High accuracy
        """.strip()
        )
        sample_docs.append(f.name)

    # 2. Document simulating OCR-extracted content
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(
            """
# Scanned Document (Simulated)

This text simulates content extracted via OCR from a scanned document.
It may contain typical OCR artifacts:

- Character errors: Sorne -> Some
- Spacing issues: word boundaries
- Mixed case: TeXt ExTrAcTiOn
- Number confusion: 0CR -> OCR

The OCR cleaning system will automatically detect and fix these issues.
        """.strip()
        )
        sample_docs.append(f.name)

    try:
        # Process documents with OCR pipeline
        results = await process_documents_with_ocr(sample_docs)

        print(f"🎉 Successfully processed {len(results)} documents!")
        print()

        # Show sample results
        if results:
            sample_doc = results[0]
            print("📋 Sample processed document:")
            print(f"   Filename: {sample_doc.metadata.filename}")
            print(f"   Text length: {len(sample_doc.full_text):,} characters")
            print(f"   Chunks: {len(sample_doc.chunks)}")

            if sample_doc.chunks:
                print("   First chunk preview:")
                preview = sample_doc.chunks[0].content[:100] + "..."
                print(f"      {repr(preview)}")

    finally:
        # Cleanup temporary files
        for doc_path in sample_docs:
            Path(doc_path).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
