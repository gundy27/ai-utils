"""Utility functions for HTML parsing and processing."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Dict

import structlog

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

logger = structlog.get_logger(__name__)


def fetch_html(url: str, timeout: int = 30) -> str:
    """Fetch HTML content from a URL.

    Args:
        url: URL to fetch HTML from
        timeout: Request timeout in seconds (default: 30)

    Returns:
        HTML content as string

    Raises:
        ImportError: If httpx is not installed
        httpx.HTTPError: If request fails
        ValueError: If URL is invalid
    """
    try:
        import httpx
    except ImportError as e:
        raise ImportError(
            "httpx library is required for URL fetching. "
            "Install with: pip install httpx>=0.25"
        ) from e

    logger.debug("fetching_html", url=url, timeout=timeout)

    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        logger.error("fetch_html_failed", url=url, error=str(e))
        raise


def extract_metadata(soup: "BeautifulSoup") -> Dict[str, Any]:
    """Extract metadata from HTML document.

    Extracts:
    - description (meta description)
    - keywords (meta keywords)
    - author (meta author)
    - Open Graph tags (og:title, og:description, og:image, og:type)
    - Twitter Card tags

    Args:
        soup: BeautifulSoup object

    Returns:
        Dictionary with metadata fields
    """
    metadata: Dict[str, Any] = {}

    # Standard meta tags
    description_tag = soup.find("meta", attrs={"name": "description"})
    if description_tag and description_tag.get("content"):
        metadata["description"] = description_tag["content"]

    keywords_tag = soup.find("meta", attrs={"name": "keywords"})
    if keywords_tag and keywords_tag.get("content"):
        metadata["keywords"] = keywords_tag["content"]

    author_tag = soup.find("meta", attrs={"name": "author"})
    if author_tag and author_tag.get("content"):
        metadata["author"] = author_tag["content"]

    # Open Graph tags
    og_tags = soup.find_all("meta", property=re.compile(r"^og:"))
    for tag in og_tags:
        prop = tag.get("property", "")
        content = tag.get("content")
        if prop and content:
            # Remove 'og:' prefix and use as key
            key = prop.replace("og:", "og_")
            metadata[key] = content

    # Twitter Card tags
    twitter_tags = soup.find_all("meta", attrs={"name": re.compile(r"^twitter:")})
    for tag in twitter_tags:
        name = tag.get("name", "")
        content = tag.get("content")
        if name and content:
            # Remove 'twitter:' prefix and use as key
            key = name.replace("twitter:", "twitter_")
            metadata[key] = content

    logger.debug("extracted_metadata", fields=list(metadata.keys()))
    return metadata


def extract_plaintext(html: str, preserve_links: bool = False) -> str:
    """Convert HTML to clean plaintext.

    Removes scripts, styles, and navigation elements. Preserves paragraph
    structure with proper spacing.

    Args:
        html: Raw HTML string
        preserve_links: If True, include link URLs in output (default: False)

    Returns:
        Clean plaintext string

    Raises:
        ImportError: If beautifulsoup4 is not installed
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise ImportError(
            "beautifulsoup4 library is required for HTML parsing. "
            "Install with: pip install beautifulsoup4>=4.12"
        ) from e

    soup = BeautifulSoup(html, "html.parser")

    # Remove script, style, nav, footer, header elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
        element.decompose()

    # Handle links if preserve_links is True
    if preserve_links:
        for link in soup.find_all("a"):
            href = link.get("href")
            if href and link.string:
                # Replace link with "text (url)" format
                link.string = f"{link.string} ({href})"

    # Get text and clean it
    text = soup.get_text(separator="\n", strip=True)
    cleaned = clean_text(text)

    logger.debug("extracted_plaintext", length=len(cleaned))
    return cleaned


def clean_text(text: str) -> str:
    """Normalize whitespace and remove excess newlines.

    Args:
        text: Text to clean

    Returns:
        Cleaned text with normalized whitespace
    """
    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with double newline (paragraph break)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove leading/trailing whitespace from entire text
    text = text.strip()

    return text
