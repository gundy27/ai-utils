"""Example demonstrating enhanced output formats."""

import asyncio
import tempfile
from pathlib import Path

from gundy_ai.data_pipelines import (
    EnhancedDocumentProcessor,
    EnhancedTextChunker,
    ProcessorConfig,
)
from gundy_ai.data_pipelines.output_formats import (
    OutputFormat,
    OutputManager,
    JSONWriter,
    NDJSONWriter,
    ParquetWriter,
)


async def main():
    """Demonstrate enhanced output formats."""
    print("📄 Enhanced Output Formats Demo")
    print("=" * 50)

    # Sample document content
    sample_text = """
# Machine Learning in Healthcare

Machine learning is revolutionizing healthcare by enabling more accurate diagnoses, personalized treatments, and efficient drug discovery processes.

## Diagnostic Applications

AI systems can analyze medical images with remarkable accuracy. Deep learning models trained on thousands of X-rays, MRIs, and CT scans can detect abnormalities that might be missed by human radiologists.

### Image Analysis
Computer vision algorithms excel at pattern recognition in medical imaging. They can identify tumors, fractures, and other pathological conditions with high precision.

### Predictive Analytics
Machine learning models can predict patient outcomes by analyzing electronic health records, lab results, and vital signs. This enables proactive interventions and better resource allocation.

## Treatment Personalization

By analyzing genetic data, medical history, and treatment responses, ML algorithms can recommend personalized treatment plans that are more effective for individual patients.

## Drug Discovery

AI accelerates drug discovery by predicting molecular behavior, identifying potential drug targets, and optimizing compound structures. This reduces the time and cost of bringing new medications to market.

## Challenges and Considerations

While promising, ML in healthcare faces challenges including data privacy, regulatory approval, and the need for interpretable models that clinicians can trust and understand.
    """

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(sample_text)
        temp_file = f.name

    # Create temporary output directory
    with tempfile.TemporaryDirectory() as temp_dir:
        output_dir = Path(temp_dir)

        try:
            print("🔄 Processing document...")

            # Process document
            doc_config = ProcessorConfig(name="output_demo")
            doc_processor = EnhancedDocumentProcessor(doc_config)
            doc_result = await doc_processor.process(temp_file)

            if not doc_result.success:
                print(f"❌ Document processing failed: {doc_result.error}")
                return

            document = doc_result.data
            print(f"✅ Document processed: {len(document.full_text)} characters")

            # Chunk the document
            chunker_config = ProcessorConfig(name="output_chunker")
            chunker = EnhancedTextChunker(
                config=chunker_config,
                strategy="structure_aware",
                chunk_size=400,
                preserve_headings=True,
            )

            chunk_result = await chunker.process(document)
            if chunk_result.success:
                document = chunk_result.data
                print(f"✅ Document chunked: {len(document.chunks)} chunks")
            print()

            # Initialize output manager
            output_manager = OutputManager()

            print("📊 Available Output Formats:")
            for format_type in output_manager.get_supported_formats():
                info = output_manager.get_format_info(format_type)
                print(f"   • {format_type.value.upper()}: {info['description']}")
            print()

            # Test individual format writers
            formats_to_test = [
                (OutputFormat.JSON, "Standard JSON format"),
                (OutputFormat.NDJSON, "Newline-delimited JSON"),
                (OutputFormat.PARQUET, "Columnar Parquet format"),
            ]

            results = {}

            for format_type, description in formats_to_test:
                print(f"📝 Writing {description}...")

                # Generate output filename
                extension = {
                    OutputFormat.JSON: ".json",
                    OutputFormat.NDJSON: ".ndjson",
                    OutputFormat.PARQUET: ".parquet",
                }[format_type]

                output_path = output_dir / f"healthcare_ml{extension}"

                # Write document
                result = await output_manager.write_document(
                    document, output_path, format_type
                )

                results[format_type] = result

                if result.success:
                    file_size_kb = result.file_size / 1024
                    print(f"   ✅ Success: {output_path.name}")
                    print(f"      File size: {file_size_kb:.1f} KB")
                    print(f"      Processing time: {result.processing_time_ms:.1f}ms")

                    # Show format-specific metadata
                    if format_type == OutputFormat.NDJSON:
                        lines = result.metadata.get("lines_written", 0)
                        print(f"      Lines written: {lines}")
                    elif format_type == OutputFormat.PARQUET:
                        rows = result.metadata.get("row_count", 0)
                        compression = result.metadata.get("compression", "unknown")
                        print(f"      Rows: {rows}, Compression: {compression}")
                else:
                    print(f"   ❌ Failed: {result.error}")
                print()

            # Test multi-format output
            print("🚀 Multi-Format Output Test...")
            multi_results = await output_manager.write_multiple_formats(
                documents=[document],
                output_directory=output_dir / "multi_format",
                formats=[OutputFormat.JSON, OutputFormat.NDJSON, OutputFormat.PARQUET],
                base_filename="healthcare_multi",
            )

            print("   Multi-format results:")
            for format_type, result in multi_results.items():
                status = "✅" if result.success else "❌"
                size_kb = result.file_size / 1024 if result.success else 0
                print(f"      {status} {format_type.value}: {size_kb:.1f} KB")
            print()

            # Compare format characteristics
            print("📊 Format Comparison:")
            print(
                f"{'Format':<10} {'Size (KB)':<12} {'Time (ms)':<12} {'Efficiency':<12}"
            )
            print("-" * 50)

            for format_type, result in results.items():
                if result.success:
                    size_kb = result.file_size / 1024
                    time_ms = result.processing_time_ms
                    efficiency = size_kb / time_ms if time_ms > 0 else 0
                    print(
                        f"{format_type.value:<10} {size_kb:<12.1f} {time_ms:<12.1f} {efficiency:<12.2f}"
                    )
            print()

            # Demonstrate format-specific features
            print("🔧 Format-Specific Features:")

            # JSON with custom formatting
            print("   JSON with custom indentation...")
            json_writer = JSONWriter(indent=4, ensure_ascii=False)
            json_result = await json_writer.write_document(
                document, output_dir / "custom_formatted.json"
            )
            if json_result.success:
                print(f"      ✅ Custom JSON: {json_result.file_size / 1024:.1f} KB")

            # NDJSON with chunk-per-line
            print("   NDJSON with chunk-per-line...")
            ndjson_writer = NDJSONWriter(chunk_per_line=True)
            ndjson_result = await ndjson_writer.write_document(
                document, output_dir / "chunks_per_line.ndjson"
            )
            if ndjson_result.success:
                lines = ndjson_result.metadata.get("lines_written", 0)
                print(f"      ✅ Chunk-per-line NDJSON: {lines} lines")

            # Parquet with different compression
            print("   Parquet with gzip compression...")
            parquet_writer = ParquetWriter(compression="gzip", chunk_per_row=True)
            parquet_result = await parquet_writer.write_document(
                document, output_dir / "compressed.parquet"
            )
            if parquet_result.success:
                size_kb = parquet_result.file_size / 1024
                rows = parquet_result.metadata.get("row_count", 0)
                print(f"      ✅ Compressed Parquet: {size_kb:.1f} KB, {rows} rows")
            print()

            print("💡 Use Case Recommendations:")
            print("   • JSON: API responses, configuration, human-readable output")
            print("   • NDJSON: Streaming processing, log analysis, ETL pipelines")
            print("   • Parquet: Analytics, data warehousing, ML feature stores")
            print()

            print("🎯 Key Benefits:")
            print("   • Multiple output formats from single processing pipeline")
            print("   • Optimized for different use cases and storage requirements")
            print("   • Preserves all metadata and chunk information")
            print("   • Efficient compression and columnar storage options")

        finally:
            # Cleanup
            Path(temp_file).unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
