"""Example demonstrating enhanced PDF processing with multiple parsers."""

import asyncio
from pathlib import Path

from gundy_ai.data_pipelines import (
    EnhancedDocumentProcessor,
    ProcessorConfig,
)


async def main():
    """Demonstrate enhanced PDF processing capabilities."""
    print("🚀 Enhanced PDF Processing Demo")
    print("=" * 50)

    # Create enhanced document processor
    config = ProcessorConfig(name="enhanced_pdf_demo")
    processor = EnhancedDocumentProcessor(
        config=config,
        pdf_parser_priority=["pdfplumber", "pymupdf", "pypdf"],
        enable_ocr_fallback=True,
        ocr_confidence_threshold=0.6,
        min_text_extraction_ratio=0.1,
    )

    print("✅ Enhanced document processor initialized")
    print(f"   Parser priority: {processor.pdf_parser_priority}")
    print(f"   OCR fallback: {processor.enable_ocr_fallback}")
    print()

    # Test with sample PDFs (you would replace these with actual PDF paths)
    test_files = [
        # Add paths to test PDFs here
        # "path/to/sample.pdf",
        # "path/to/scanned_document.pdf",
        # "path/to/multi_column.pdf",
    ]

    if not test_files:
        print("📝 No test files provided. Here's how to use the enhanced processor:")
        print()
        print("```python")
        print(
            "from gundy_ai.data_pipelines import EnhancedDocumentProcessor, ProcessorConfig"
        )
        print()
        print("# Initialize processor")
        print("config = ProcessorConfig(name='pdf_processor')")
        print("processor = EnhancedDocumentProcessor(")
        print("    config=config,")
        print("    pdf_parser_priority=['pdfplumber', 'pymupdf', 'pypdf'],")
        print("    enable_ocr_fallback=True")
        print(")")
        print()
        print("# Process a PDF")
        print("result = await processor.process('document.pdf')")
        print()
        print("if result.success:")
        print("    doc = result.data")
        print("    print(f'Extracted {len(doc.full_text)} characters')")
        print(
            "    print(f'Parser used: {doc.metadata.custom_metadata[\"parser_used\"]}')"
        )
        print("    print(f'OCR used: {doc.metadata.custom_metadata[\"ocr_used\"]}')")
        print(
            "    print(f'Processing time: {doc.metadata.custom_metadata[\"processing_time_ms\"]:.1f}ms')"
        )
        print("```")
        print()
        return

    # Process each test file
    for file_path in test_files:
        path = Path(file_path)
        if not path.exists():
            print(f"⚠️  File not found: {file_path}")
            continue

        print(f"📄 Processing: {path.name}")
        print("-" * 30)

        try:
            result = await processor.process(str(path))

            if result.success:
                doc = result.data
                metadata = doc.metadata.custom_metadata

                print("✅ Success!")
                print(f"   📊 Text length: {len(doc.full_text):,} characters")
                print(f"   📄 Pages: {doc.metadata.page_count}")
                print(f"   🔧 Parser used: {metadata.get('parser_used', 'unknown')}")
                print(f"   👁️  OCR used: {metadata.get('ocr_used', False)}")
                print(
                    f"   ⏱️  Processing time: {metadata.get('processing_time_ms', 0):.1f}ms"
                )

                # Show parsing attempts
                attempts = metadata.get("parsing_attempts", [])
                if attempts:
                    print("   🔄 Parsing attempts:")
                    for attempt in attempts:
                        status = "✅" if attempt["success"] else "❌"
                        print(
                            f"      {status} {attempt['parser']}: "
                            f"{attempt['text_length']:,} chars, "
                            f"{attempt['processing_time_ms']:.1f}ms"
                        )

                # Show sample text
                sample_text = (
                    doc.full_text[:200] + "..."
                    if len(doc.full_text) > 200
                    else doc.full_text
                )
                print(f"   📝 Sample text: {repr(sample_text)}")

            else:
                print(f"❌ Failed: {result.error}")

        except Exception as e:
            print(f"💥 Exception: {str(e)}")

        print()

    print("🎯 Enhanced PDF Processing Features:")
    print("   • Multiple parser backends (PDFPlumber, PyMuPDF, PyPDF2)")
    print("   • Automatic fallback strategies")
    print("   • OCR support for scanned documents")
    print("   • Layout preservation and table extraction")
    print("   • Detailed positioning information")
    print("   • Quality assessment and parser selection")
    print("   • Comprehensive metadata and timing")


if __name__ == "__main__":
    asyncio.run(main())
