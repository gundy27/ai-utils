"""Example usage of HTML parser for document extraction."""

from gundy_ai.extractors import ParserRegistry, HTMLParser
from gundy_ai.extractors.parsers.html_utils import extract_plaintext


def main():
    """Demonstrate HTML parsing capabilities."""

    # Create sample HTML content
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Documentation</title>
        <meta name="description" content="Learn about AI and machine learning">
        <meta name="keywords" content="AI, ML, deep learning">
        <meta property="og:title" content="AI Docs">
    </head>
    <body>
        <h1>Introduction to AI</h1>
        <p>Artificial Intelligence (AI) is transforming technology.</p>
        
        <h2>Machine Learning</h2>
        <p>Machine learning is a subset of AI focused on learning from data.</p>
        
        <h2>Resources</h2>
        <p>Check out these helpful resources:</p>
        <a href="https://example.com/tutorial">AI Tutorial</a>
        <a href="https://example.com/docs">Documentation</a>
    </body>
    </html>
    """

    # Save to file for demonstration
    with open("sample.html", "w") as f:
        f.write(sample_html)

    print("=" * 70)
    print("HTML Parser Example")
    print("=" * 70)

    # Example 1: Parse local HTML file using registry
    print("\n1. Parsing local HTML file using registry:")
    print("-" * 70)

    registry = ParserRegistry()
    registry.register(HTMLParser())
    parser = registry.get_parser(".html")
    chunks = parser.parse("sample.html")

    print(f"Extracted {len(chunks)} chunks:\n")

    for i, chunk in enumerate(chunks, 1):
        chunk_type = chunk.metadata.get("type")
        print(f"Chunk {i} ({chunk_type}):")
        print(f"  Text: {chunk.text[:100]}...")
        if chunk_type == "heading":
            print(f"  Level: H{chunk.metadata.get('level')}")
        if chunk_type == "link":
            print(f"  URL: {chunk.metadata.get('href')}")
        print()

    # Example 2: Parse without links
    print("\n2. Parsing without link extraction:")
    print("-" * 70)

    parser_no_links = HTMLParser(extract_links=False)
    chunks_no_links = parser_no_links.parse("sample.html")

    link_chunks = [c for c in chunks_no_links if c.metadata.get("type") == "link"]
    print(f"Link chunks: {len(link_chunks)} (should be 0)")

    # Example 3: Filter chunks by type
    print("\n3. Filtering chunks by type:")
    print("-" * 70)

    # Get only paragraphs
    paragraphs = [c for c in chunks if c.metadata.get("type") == "paragraph"]
    print(f"\nParagraphs ({len(paragraphs)}):")
    for p in paragraphs:
        print(f"  - {p.text}")

    # Get only headings
    headings = [c for c in chunks if c.metadata.get("type") == "heading"]
    print(f"\nHeadings ({len(headings)}):")
    for h in headings:
        level = h.metadata.get("level")
        print(f"  H{level}: {h.text}")

    # Get metadata
    metadata_chunks = [c for c in chunks if c.metadata.get("type") == "metadata"]
    print(f"\nMetadata ({len(metadata_chunks)}):")
    if metadata_chunks:
        meta = metadata_chunks[0]
        print(f"  Description: {meta.metadata.get('description')}")
        print(f"  Keywords: {meta.metadata.get('keywords')}")
        print(f"  OG Title: {meta.metadata.get('og_title')}")

    # Example 4: Extract plaintext
    print("\n4. Extract as plaintext:")
    print("-" * 70)

    plaintext = extract_plaintext(sample_html)
    print(plaintext)

    # Example 5: Extract plaintext with links
    print("\n5. Extract plaintext with links preserved:")
    print("-" * 70)

    plaintext_with_links = extract_plaintext(sample_html, preserve_links=True)
    print(plaintext_with_links)

    # Example 6: Parse from URL (demonstration - would work with real URL)
    print("\n6. Parsing from URL (example):")
    print("-" * 70)
    print("parser = HTMLParser()")
    print('chunks = parser.parse("https://example.com/page.html")')
    print("# This would fetch and parse content from the URL")

    # Example 7: Integration with chunker
    print("\n7. Integration with chunker:")
    print("-" * 70)

    try:
        from gundy_ai.chunker import TokenAwareChunker

        # Combine all text from chunks
        all_text = "\n\n".join(
            chunk.text
            for chunk in chunks
            if chunk.metadata.get("type") in ["paragraph", "heading"]
        )

        chunker = TokenAwareChunker(max_tokens=100, overlap_tokens=20)
        text_chunks = chunker.chunk(all_text)

        print(f"Created {len(text_chunks)} token-aware chunks")
        print(f"First chunk tokens: {text_chunks[0].token_count}")
    except ImportError:
        print("(gundy-ai-chunker not installed - skipping this example)")

    # Example 8: Health check
    print("\n8. Health check:")
    print("-" * 70)

    html_parser = HTMLParser()
    healthy = html_parser.health_check()
    print(f"Parser dependencies available: {healthy}")

    # Clean up
    import os

    os.remove("sample.html")
    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
