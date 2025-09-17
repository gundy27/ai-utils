"""Command-line interface for data pipelines."""

import asyncio
import sys
from pathlib import Path

import click
import structlog

from .pipeline import create_default_document_pipeline

logger = structlog.get_logger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def main(verbose: bool):
    """Data processing pipeline CLI."""
    # Configure logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


@main.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output directory for results")
@click.option(
    "--model", default="text-embedding-3-small", help="Embedding model to use"
)
@click.option("--api-key", help="OpenAI API key")
@click.option("--base-url", help="OpenAI API base URL")
@click.option("--chunk-size", default=1000, help="Chunk size in tokens")
@click.option("--chunk-overlap", default=200, help="Chunk overlap in tokens")
@click.option("--batch-size", default=100, help="Batch size for embedding generation")
@click.option("--max-concurrent", default=5, help="Max concurrent document processing")
def process_documents(
    input_path: str,
    output: str | None,
    model: str,
    api_key: str | None,
    base_url: str | None,
    chunk_size: int,
    chunk_overlap: int,
    batch_size: int,
    max_concurrent: int,
):
    """Process documents through the data pipeline."""

    async def _process():
        input_path_obj = Path(input_path)

        # Find documents to process
        documents = []
        if input_path_obj.is_file():
            documents = [str(input_path_obj)]
        elif input_path_obj.is_dir():
            # Find all supported document types
            extensions = {".txt", ".pdf", ".docx", ".html", ".htm", ".md", ".markdown"}
            for ext in extensions:
                documents.extend(input_path_obj.glob(f"**/*{ext}"))
            documents = [str(doc) for doc in documents]
        else:
            click.echo(f"Error: {input_path} is not a file or directory", err=True)
            sys.exit(1)

        if not documents:
            click.echo("No documents found to process", err=True)
            sys.exit(1)

        click.echo(f"Found {len(documents)} documents to process")

        # Create pipeline configuration
        embedding_config = {
            "model": model,
            "api_key": api_key,
            "base_url": base_url,
            "max_batch_size": batch_size,
        }

        # Create pipeline
        try:
            pipeline = create_default_document_pipeline(
                embedding_config=embedding_config,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            # Set max concurrent processing
            pipeline.config.max_concurrent_documents = max_concurrent

            click.echo("Starting document processing...")

            # Process documents
            result = await pipeline.process_documents(documents)

            # Display results
            click.echo("\nProcessing completed!")
            click.echo(f"  Successfully processed: {result.processed_count}")
            click.echo(f"  Failed: {result.failed_count}")
            click.echo(f"  Success rate: {result.get_success_rate():.1f}%")
            click.echo(f"  Execution time: {result.execution_time_ms}ms")

            # Show failed documents
            if result.failed_count > 0:
                click.echo("\nFailed documents:")
                for failed_result in result.results:
                    if not failed_result.success:
                        click.echo(f"  - {failed_result.error}")

            # Save results if output directory specified
            if output:
                output_dir = Path(output)
                output_dir.mkdir(parents=True, exist_ok=True)

                click.echo(f"\nSaving results to {output_dir}")

                for i, successful_result in enumerate(result.results):
                    if successful_result.success:
                        embedded_doc = successful_result.data

                        # Save metadata
                        metadata_file = output_dir / f"document_{i}_metadata.json"
                        metadata_file.write_text(
                            f"""{{
    "filename": "{embedded_doc.document.metadata.filename}",
    "document_type": "{embedded_doc.document.metadata.document_type.value}",
    "chunk_count": {embedded_doc.get_embedding_count()},
    "total_tokens": {embedded_doc.get_total_embeddings_tokens()},
    "embedding_model": "{model}"
}}"""
                        )

                        # Save chunks
                        chunks_file = output_dir / f"document_{i}_chunks.txt"
                        with chunks_file.open("w", encoding="utf-8") as f:
                            for j, chunk in enumerate(embedded_doc.document.chunks):
                                f.write(f"=== Chunk {j} ===\n")
                                f.write(f"Tokens: {chunk.token_count}\n")
                                f.write(
                                    f"Characters: {chunk.start_char}-{chunk.end_char}\n"
                                )
                                f.write(f"Content:\n{chunk.content}\n\n")

                click.echo(f"Results saved to {output_dir}")

        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)
            logger.error("pipeline.error", error=str(e))
            sys.exit(1)

    asyncio.run(_process())


@main.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file for embeddings")
@click.option(
    "--model", default="text-embedding-3-small", help="Embedding model to use"
)
@click.option("--api-key", help="OpenAI API key")
@click.option("--batch-size", default=100, help="Batch size for embedding generation")
def generate_embeddings(
    input_path: str,
    output: str | None,
    model: str,
    api_key: str | None,
    batch_size: int,
):
    """Generate embeddings for text files."""

    async def _generate():
        input_path_obj = Path(input_path)

        if not input_path_obj.is_file():
            click.echo(f"Error: {input_path} is not a file", err=True)
            sys.exit(1)

        # Read text file
        try:
            text = input_path_obj.read_text(encoding="utf-8")
        except Exception as e:
            click.echo(f"Error reading file: {str(e)}", err=True)
            sys.exit(1)

        click.echo(f"Generating embeddings for {input_path_obj.name}")
        click.echo(f"Text length: {len(text)} characters")

        # Create embedding configuration
        embedding_config = {
            "model": model,
            "api_key": api_key,
            "max_batch_size": batch_size,
        }

        # Create pipeline
        try:
            pipeline = create_default_document_pipeline(embedding_config)

            # Process single document
            result = await pipeline.process_single_document(str(input_path_obj))

            if not result.success:
                click.echo(f"Error processing document: {result.error}", err=True)
                sys.exit(1)

            embedded_doc = result.data

            click.echo("\nProcessing completed!")
            click.echo(f"  Chunks created: {embedded_doc.get_embedding_count()}")
            click.echo(f"  Total tokens: {embedded_doc.get_total_embeddings_tokens()}")
            click.echo(
                f"  Embedding dimensions: {len(embedded_doc.embeddings[0].vector) if embedded_doc.embeddings else 0}"
            )

            # Save embeddings if output specified
            if output:
                output_file = Path(output)

                # Save as JSON
                import json

                embeddings_data = {
                    "document": {
                        "filename": embedded_doc.document.metadata.filename,
                        "document_type": embedded_doc.document.metadata.document_type.value,
                        "total_tokens": embedded_doc.get_total_embeddings_tokens(),
                    },
                    "embeddings": [
                        {
                            "text": emb.text,
                            "vector": emb.vector,
                            "token_count": emb.token_count,
                            "metadata": emb.metadata,
                        }
                        for emb in embedded_doc.embeddings
                    ],
                }

                output_file.write_text(json.dumps(embeddings_data, indent=2))
                click.echo(f"Embeddings saved to {output_file}")

        except Exception as e:
            click.echo(f"Error: {str(e)}", err=True)
            logger.error("embedding.generation.error", error=str(e))
            sys.exit(1)

    asyncio.run(_generate())


if __name__ == "__main__":
    main()
