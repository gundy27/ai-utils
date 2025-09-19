"""Command-line interface for the downloader."""

import asyncio
import json
from typing import Any

import click
import structlog

from .base import DownloadResult
from .downloader import UniversalDownloader
from .sources import HTTPSource, LocalFileSource, S3Source

logger = structlog.get_logger(__name__)


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option(
    "--destination",
    "-d",
    type=click.Path(),
    help="Default destination directory",
)
@click.option("--max-retries", default=3, help="Maximum retry attempts")
@click.option("--timeout", default=300, help="Timeout in seconds")
@click.option("--rate-limit", default=1.0, help="Rate limit (requests per second)")
@click.option("--max-concurrent", default=3, help="Maximum concurrent downloads")
@click.pass_context
def cli(
    ctx: click.Context,
    verbose: bool,
    destination: str | None,
    max_retries: int,
    timeout: int,
    rate_limit: float,
    max_concurrent: int,
):
    """Universal file downloader with support for HTTP, FTP, SFTP, S3, and local files."""

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

    # Set log level
    if verbose:
        import logging

        logging.basicConfig(level=logging.DEBUG)

    # Create downloader instance
    ctx.obj = {
        "downloader": UniversalDownloader(
            max_retries=max_retries,
            timeout_seconds=timeout,
            max_concurrent_downloads=max_concurrent,
            rate_limit_per_second=rate_limit,
            destination_directory=destination,
        ),
    }


@cli.command()
@click.option("--url", required=True, help="URL to download")
@click.option("--headers", help="JSON string of HTTP headers")
@click.option("--auth", help="JSON string with username/password")
@click.option("--method", default="GET", help="HTTP method")
@click.option("--destination", "-d", type=click.Path(), help="Destination path")
@click.option("--filename", "-f", help="Custom filename")
@click.pass_context
def http(
    ctx: click.Context,
    url: str,
    headers: str | None,
    auth: str | None,
    method: str,
    destination: str | None,
    filename: str | None,
):
    """Download from HTTP/HTTPS URL."""

    downloader = ctx.obj["downloader"]

    # Parse headers
    parsed_headers = {}
    if headers:
        try:
            parsed_headers = json.loads(headers)
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON in headers", err=True)
            return

    # Parse auth
    parsed_auth = None
    if auth:
        try:
            parsed_auth = json.loads(auth)
        except json.JSONDecodeError:
            click.echo("Error: Invalid JSON in auth", err=True)
            return

    # Create source
    source = HTTPSource(
        identifier=url,
        url=url,
        headers=parsed_headers,
        auth=parsed_auth,
        method=method,
    )

    # Download
    async def download():
        result = await downloader.download(source, destination, filename)
        _handle_result(result)

    asyncio.run(download())


@cli.command()
@click.option("--bucket", required=True, help="S3 bucket name")
@click.option("--key", required=True, help="S3 object key")
@click.option("--region", help="AWS region")
@click.option("--access-key-id", help="AWS access key ID")
@click.option("--secret-access-key", help="AWS secret access key")
@click.option("--session-token", help="AWS session token")
@click.option("--endpoint-url", help="Custom S3 endpoint URL")
@click.option("--version-id", help="S3 object version ID")
@click.option("--destination", "-d", type=click.Path(), help="Destination path")
@click.option("--filename", "-f", help="Custom filename")
@click.pass_context
def s3(
    ctx: click.Context,
    bucket: str,
    key: str,
    region: str | None,
    access_key_id: str | None,
    secret_access_key: str | None,
    session_token: str | None,
    endpoint_url: str | None,
    version_id: str | None,
    destination: str | None,
    filename: str | None,
):
    """Download from AWS S3."""

    downloader = ctx.obj["downloader"]

    # Create source
    source = S3Source(
        identifier=f"{bucket}/{key}",
        bucket=bucket,
        key=key,
        region=region,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        session_token=session_token,
        endpoint_url=endpoint_url,
        version_id=version_id,
    )

    # Download
    async def download():
        result = await downloader.download(source, destination, filename)
        _handle_result(result)

    asyncio.run(download())


@cli.command()
@click.option(
    "--source-path",
    required=True,
    type=click.Path(exists=True),
    help="Source file path",
)
@click.option("--destination", "-d", type=click.Path(), help="Destination path")
@click.option("--filename", "-f", help="Custom filename")
@click.option("--move", is_flag=True, help="Move instead of copy")
@click.pass_context
def local(
    ctx: click.Context,
    source_path: str,
    destination: str | None,
    filename: str | None,
    move: bool,
):
    """Copy or move local file."""

    downloader = ctx.obj["downloader"]

    # Create source
    source = LocalFileSource(
        identifier=source_path,
        file_path=source_path,
        move_file=move,
    )

    # Download
    async def download():
        result = await downloader.download(source, destination, filename)
        _handle_result(result)

    asyncio.run(download())


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="JSON config file",
)
@click.pass_context
def batch(ctx: click.Context, config: str):
    """Download multiple files from JSON config."""

    downloader = ctx.obj["downloader"]

    # Load config
    try:
        with open(config) as f:
            config_data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        click.echo(f"Error loading config: {e}", err=True)
        return

    # Validate config
    if not isinstance(config_data, list):
        click.echo("Error: Config must be a list of download tasks", err=True)
        return

    # Create sources
    sources = []
    for task in config_data:
        source = _create_source_from_config(task)
        if source:
            sources.append(source)

    if not sources:
        click.echo("Error: No valid sources found in config", err=True)
        return

    # Download
    async def download():
        results = await downloader.download_multiple(sources)

        # Print summary
        successful = sum(1 for r in results.values() if r.success)
        failed = len(results) - successful

        click.echo("\nDownload Summary:")
        click.echo(f"Total: {len(results)}")
        click.echo(f"Successful: {successful}")
        click.echo(f"Failed: {failed}")

        # Print failed downloads
        if failed > 0:
            click.echo("\nFailed downloads:")
            for identifier, result in results.items():
                if not result.success:
                    click.echo(f"  {identifier}: {result.error}")

    asyncio.run(download())


@cli.command()
@click.pass_context
def stats(ctx: click.Context):
    """Show downloader statistics."""

    downloader = ctx.obj["downloader"]
    stats_data = downloader.get_stats()

    click.echo("Downloader Statistics:")
    click.echo(json.dumps(stats_data, indent=2))


def _handle_result(result: DownloadResult) -> None:
    """Handle download result."""

    if result.success:
        click.echo("✓ Download successful!")
        click.echo(f"  File: {result.local_file.path}")
        click.echo(f"  Size: {result.bytes_downloaded} bytes")
        click.echo(f"  Time: {result.download_time_seconds:.2f}s")
        click.echo(f"  Checksum: {result.local_file.checksum.value}")
    else:
        click.echo(f"✗ Download failed: {result.error}", err=True)


def _create_source_from_config(task: dict) -> Any | None:
    """Create source from config task."""

    source_type = task.get("type")

    if source_type == "http":
        return HTTPSource(
            identifier=task.get("id", task["url"]),
            url=task["url"],
            headers=task.get("headers", {}),
            auth=task.get("auth"),
            method=task.get("method", "GET"),
        )

    if source_type == "s3":
        return S3Source(
            identifier=task.get("id", f"{task['bucket']}/{task['key']}"),
            bucket=task["bucket"],
            key=task["key"],
            region=task.get("region"),
            access_key_id=task.get("access_key_id"),
            secret_access_key=task.get("secret_access_key"),
            session_token=task.get("session_token"),
            endpoint_url=task.get("endpoint_url"),
            version_id=task.get("version_id"),
        )

    if source_type == "local":
        return LocalFileSource(
            identifier=task.get("id", task["file_path"]),
            file_path=task["file_path"],
            move_file=task.get("move", False),
        )

    click.echo(f"Unknown source type: {source_type}", err=True)
    return None


def main():
    """Main CLI entry point."""
    cli()


if __name__ == "__main__":
    main()
