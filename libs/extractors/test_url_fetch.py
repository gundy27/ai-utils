#!/usr/bin/env python3
"""Quick test script for HTML parser with public URLs."""

from gundy_ai.extractors import HTMLParser

# Test with a simple, stable public URL
urls_to_test = [
    "https://example.com",  # Simple, minimal HTML
    "https://www.python.org",  # More complex with structure
    "https://en.wikipedia.org/wiki/Artificial_intelligence",  # Rich content
]


def test_url(url: str):
    """Test parsing a single URL."""
    print(f"\n{'='*70}")
    print(f"Testing: {url}")
    print("=" * 70)

    try:
        parser = HTMLParser(extract_links=False)  # Disable links for cleaner output
        chunks = parser.parse(url)

        print(f"\n✓ Successfully parsed! Extracted {len(chunks)} chunks\n")

        # Show title
        title_chunks = [c for c in chunks if c.metadata.get("type") == "title"]
        if title_chunks:
            print(f"Title: {title_chunks[0].text}\n")

        # Show headings
        headings = [c for c in chunks if c.metadata.get("type") == "heading"]
        print(f"Headings ({len(headings)}):")
        for h in headings[:5]:  # Show first 5
            level = h.metadata.get("level")
            print(f"  H{level}: {h.text[:80]}")
        if len(headings) > 5:
            print(f"  ... and {len(headings) - 5} more")

        # Show paragraphs
        paragraphs = [c for c in chunks if c.metadata.get("type") == "paragraph"]
        print(f"\nParagraphs ({len(paragraphs)}):")
        for p in paragraphs[:3]:  # Show first 3
            print(f"  - {p.text[:100]}...")
        if len(paragraphs) > 3:
            print(f"  ... and {len(paragraphs) - 3} more")

        # Show metadata
        metadata_chunks = [c for c in chunks if c.metadata.get("type") == "metadata"]
        if metadata_chunks:
            print("\nMetadata:")
            meta = metadata_chunks[0].metadata
            if meta.get("description"):
                print(f"  Description: {meta.get('description')[:100]}...")
            if meta.get("og_title"):
                print(f"  OG Title: {meta.get('og_title')}")

    except Exception as e:
        print(f"✗ Failed: {e}")


if __name__ == "__main__":
    print("HTML Parser URL Test")
    print("=" * 70)

    # Test with example.com (simple and fast)
    test_url(urls_to_test[0])

    # Uncomment to test more URLs:
    # for url in urls_to_test[1:]:
    #     test_url(url)

    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)
