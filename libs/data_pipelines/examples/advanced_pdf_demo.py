"""Comprehensive PDF processing demo with multiple parsers, OCR, and text cleaning."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.data_pipelines import (
    DocumentProcessor,
    ProcessorConfig,
    EnhancedTextChunker,
    ChunkingStrategy,
    configure_for_openai,
)


async def create_sample_pdf():
    """Create a sample PDF for testing (placeholder - in real use, you'd have actual PDFs)."""
    # In a real scenario, you would have actual PDF files
    # For this demo, we'll create a text file as a placeholder
    content = """
# Advanced PDF Processing Demo

This document demonstrates the advanced PDF processing capabilities of the data_pipelines library.

## Multiple Parser Support

The library supports multiple PDF parsers:
- PyMuPDF (pymupdf) - High performance, good for complex layouts
- pdfplumber - Excellent for tables and precise text extraction
- PyPDF2 (pypdf) - Lightweight, good for simple documents
- OCR Fallback - For scanned documents or when text extraction fails

## OCR Integration

When standard text extraction fails or produces insufficient text, the system can automatically fall back to OCR processing using Tesseract.

### OCR Features:
- Automatic fallback when text extraction ratio is too low
- Configurable confidence thresholds
- Multi-language support
- Image preprocessing for better accuracy

## Text Cleaning

The system includes specialized text cleaning for:
- PDF artifacts (headers, footers, page numbers)
- OCR errors (character substitutions, spacing issues)
- General text normalization

## Configuration Options

The processor can be configured for different use cases:
- Academic papers with complex layouts
- Scanned documents requiring OCR
- Simple text documents
- Multi-column layouts
    """.strip()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        return f.name


async def demonstrate_basic_pdf_processing():
    """Demonstrate basic PDF processing."""
    print("📄 Basic PDF Processing")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_pdf()

    try:
        # Basic processor (simple text extraction)
        basic_processor = DocumentProcessor(
            config=ProcessorConfig(name="basic_pdf_processor")
        )

        result = await basic_processor.process(doc_path)

        if result.success:
            document = result.data
            print(f"✅ Basic processing successful")
            print(f"   📊 Text length: {len(document.full_text):,} characters")
            print(f"   📄 Word count: {document.metadata.word_count or 0}")
            print(f"   🔧 Parser used: Basic text extraction")

            # Show sample text
            preview = (
                document.full_text[:200] + "..."
                if len(document.full_text) > 200
                else document.full_text
            )
            print(f"   📝 Preview: {repr(preview)}")
        else:
            print(f"❌ Basic processing failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_advanced_pdf_processing():
    """Demonstrate advanced PDF processing with multiple parsers."""
    print("🚀 Advanced PDF Processing")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_pdf()

    try:
        # Advanced processor with multiple parsers
        advanced_processor = DocumentProcessor(
            config=ProcessorConfig(name="advanced_pdf_processor"),
            pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf", "ocr_fallback"],
            enable_ocr_fallback=True,
            ocr_confidence_threshold=0.6,
            min_text_extraction_ratio=0.1,
            enable_text_cleaning=True,
            text_cleaning_strategy="auto",
        )

        result = await advanced_processor.process(doc_path)

        if result.success:
            document = result.data
            metadata = result.metadata

            print(f"✅ Advanced processing successful")
            print(f"   📊 Text length: {len(document.full_text):,} characters")
            print(f"   📄 Word count: {document.metadata.word_count or 0}")
            print(f"   🔧 Parser used: {metadata.get('parser_used', 'unknown')}")

            # Show parsing attempts if available
            parsing_attempts = metadata.get("parsing_attempts", [])
            if parsing_attempts:
                print(f"   🔄 Parsing attempts:")
                for attempt in parsing_attempts:
                    status = "✅" if attempt["success"] else "❌"
                    parser = attempt["parser"]
                    if attempt["success"]:
                        text_len = attempt.get("text_length", 0)
                        print(f"      {status} {parser}: {text_len:,} characters")
                    else:
                        error = attempt.get("error", "unknown error")
                        print(f"      {status} {parser}: {error}")

            # Show confidence if OCR was used
            confidence = metadata.get("confidence")
            if confidence:
                print(f"   🎯 OCR confidence: {confidence:.1%}")

            # Show sample text
            preview = (
                document.full_text[:200] + "..."
                if len(document.full_text) > 200
                else document.full_text
            )
            print(f"   📝 Preview: {repr(preview)}")
        else:
            print(f"❌ Advanced processing failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_ocr_specific_processing():
    """Demonstrate OCR-specific processing configurations."""
    print("👁️ OCR-Specific Processing")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_pdf()

    try:
        # OCR-focused processor
        ocr_processor = DocumentProcessor(
            config=ProcessorConfig(name="ocr_processor"),
            pdf_parser_priority=["ocr_fallback"],  # Force OCR
            enable_ocr_fallback=True,
            ocr_confidence_threshold=0.5,  # Lower threshold for demo
            enable_text_cleaning=True,
            text_cleaning_strategy="ocr",  # OCR-specific cleaning
        )

        result = await ocr_processor.process(doc_path)

        if result.success:
            document = result.data
            metadata = result.metadata

            print(f"✅ OCR processing successful")
            print(f"   📊 Text length: {len(document.full_text):,} characters")
            print(f"   📄 Word count: {document.metadata.word_count or 0}")
            print(f"   🔧 Parser used: {metadata.get('parser_used', 'unknown')}")

            # Show OCR-specific metadata
            confidence = metadata.get("confidence")
            if confidence:
                print(f"   🎯 OCR confidence: {confidence:.1%}")

            pages_processed = metadata.get("pages_processed")
            if pages_processed:
                print(f"   📄 Pages processed: {pages_processed}")

            # Show sample text
            preview = (
                document.full_text[:200] + "..."
                if len(document.full_text) > 200
                else document.full_text
            )
            print(f"   📝 Preview: {repr(preview)}")
        else:
            print(f"❌ OCR processing failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_configuration_presets():
    """Demonstrate different configuration presets for various use cases."""
    print("⚙️ Configuration Presets")
    print("=" * 40)

    # Create sample document
    doc_path = await create_sample_pdf()

    try:
        configurations = [
            {
                "name": "Academic Papers",
                "description": "Complex layouts, multiple columns, figures",
                "config": {
                    "pdf_parser_priority": ["pymupdf", "pdfplumber", "pypdf"],
                    "enable_ocr_fallback": True,
                    "enable_text_cleaning": True,
                    "text_cleaning_strategy": "pdf",
                },
            },
            {
                "name": "Scanned Documents",
                "description": "Image-based PDFs requiring OCR",
                "config": {
                    "pdf_parser_priority": ["ocr_fallback"],
                    "enable_ocr_fallback": True,
                    "ocr_confidence_threshold": 0.7,
                    "enable_text_cleaning": True,
                    "text_cleaning_strategy": "ocr",
                },
            },
            {
                "name": "Simple Documents",
                "description": "Basic text documents, fast processing",
                "config": {
                    "pdf_parser_priority": ["pypdf"],
                    "enable_ocr_fallback": False,
                    "enable_text_cleaning": False,
                },
            },
            {
                "name": "High Accuracy",
                "description": "Maximum accuracy, all parsers and cleaning",
                "config": {
                    "pdf_parser_priority": [
                        "pymupdf",
                        "pdfplumber",
                        "pypdf",
                        "ocr_fallback",
                    ],
                    "enable_ocr_fallback": True,
                    "ocr_confidence_threshold": 0.8,
                    "min_text_extraction_ratio": 0.05,
                    "enable_text_cleaning": True,
                    "text_cleaning_strategy": "auto",
                },
            },
        ]

        for config_info in configurations:
            print(f"\n📋 {config_info['name']}:")
            print(f"   Use case: {config_info['description']}")
            print("   Configuration:")
            for key, value in config_info["config"].items():
                print(f"      {key}: {value}")

            # Create processor with this configuration
            processor = DocumentProcessor(
                config=ProcessorConfig(
                    name=f"preset_{config_info['name'].lower().replace(' ', '_')}"
                ),
                **config_info["config"],
            )

            # Process document
            result = await processor.process(doc_path)

            if result.success:
                document = result.data
                metadata = result.metadata

                print(f"   ✅ Processing successful")
                print(f"      📊 Text length: {len(document.full_text):,} characters")
                print(f"      🔧 Parser used: {metadata.get('parser_used', 'unknown')}")

                # Show confidence if available
                confidence = metadata.get("confidence")
                if confidence:
                    print(f"      🎯 Confidence: {confidence:.1%}")
            else:
                print(f"   ❌ Processing failed: {result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def demonstrate_chunking_integration():
    """Demonstrate integration with chunking for complete document processing."""
    print("🔗 Integration with Chunking")
    print("=" * 40)

    # Configure for optimal chunking
    configure_for_openai("gpt-4")

    # Create sample document
    doc_path = await create_sample_pdf()

    try:
        # Process document
        processor = DocumentProcessor(
            config=ProcessorConfig(name="integrated_processor"),
            pdf_parser_priority=["pymupdf", "pdfplumber", "pypdf"],
            enable_text_cleaning=True,
        )

        doc_result = await processor.process(doc_path)

        if doc_result.success:
            document = doc_result.data

            # Chunk the document
            chunker = EnhancedTextChunker(
                config=ProcessorConfig(name="chunker"),
                strategy=ChunkingStrategy.SEMANTIC,
            )

            chunk_result = await chunker.process(document)

            if chunk_result.success:
                chunked_doc = chunk_result.data

                print(f"✅ Complete processing successful")
                print(f"   📄 Original text: {len(document.full_text):,} characters")
                print(f"   🧩 Chunks created: {len(chunked_doc.chunks)}")

                if chunked_doc.chunks:
                    # Show chunk statistics
                    chunk_sizes = [len(chunk.content) for chunk in chunked_doc.chunks]
                    avg_size = sum(chunk_sizes) / len(chunk_sizes)
                    max_size = max(chunk_sizes)
                    min_size = min(chunk_sizes)

                    print(f"   📊 Chunk statistics:")
                    print(f"      Average size: {avg_size:.0f} characters")
                    print(f"      Size range: {min_size} - {max_size} characters")

                    # Show first chunk preview
                    first_chunk = chunked_doc.chunks[0]
                    preview = (
                        first_chunk.content[:150] + "..."
                        if len(first_chunk.content) > 150
                        else first_chunk.content
                    )
                    print(f"   📝 First chunk preview: {repr(preview)}")
            else:
                print(f"❌ Chunking failed: {chunk_result.error}")
        else:
            print(f"❌ Document processing failed: {doc_result.error}")

    finally:
        Path(doc_path).unlink(missing_ok=True)

    print()


async def main():
    """Main demo function."""
    print("🚀 Advanced PDF Processing Demo")
    print("=" * 60)
    print()
    print("This demo showcases the advanced PDF processing capabilities")
    print("of the data_pipelines library, including:")
    print("• Multiple PDF parsers with automatic fallback")
    print("• OCR integration for scanned documents")
    print("• Advanced text cleaning and normalization")
    print("• Configurable processing strategies")
    print("• Integration with semantic chunking")
    print()

    await demonstrate_basic_pdf_processing()
    await demonstrate_advanced_pdf_processing()
    await demonstrate_ocr_specific_processing()
    await demonstrate_configuration_presets()
    await demonstrate_chunking_integration()

    print("🎯 Key Takeaways:")
    print("   ✅ Single DocumentProcessor handles both basic and advanced use cases")
    print("   ✅ Automatic parser fallback ensures robust text extraction")
    print("   ✅ OCR integration handles scanned documents seamlessly")
    print("   ✅ Text cleaning improves output quality")
    print("   ✅ Configurable for different document types and use cases")
    print("   ✅ Integrates seamlessly with chunking and other pipeline components")
    print()

    print("💡 Usage Tips:")
    print("   • Start with basic mode for simple documents")
    print("   • Enable advanced features for complex or scanned PDFs")
    print("   • Use configuration presets for common use cases")
    print("   • Monitor parsing attempts to optimize parser priority")
    print("   • Combine with semantic chunking for optimal LLM input")


if __name__ == "__main__":
    asyncio.run(main())
