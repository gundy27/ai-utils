"""Example demonstrating the plugin system."""

import asyncio
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from gundy_ai.data_pipelines.plugins import (
    PluginManager,
    PluginMetadata,
    ParserPlugin,
    ChunkerPlugin,
    OutputPlugin,
)


# Example Custom Parser Plugin
class CustomTextParser(ParserPlugin):
    """Example custom text parser plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom_text_parser",
            version="1.0.0",
            description="Custom parser for special text formats",
            author="Demo Author",
            category="parser",
            dependencies=[],
            config_schema={
                "encoding": {
                    "type": str,
                    "required": False,
                    "default": "utf-8",
                    "description": "Text encoding to use",
                },
                "strip_whitespace": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Whether to strip whitespace",
                },
            },
        )

    async def initialize(self) -> bool:
        self.logger.info("initializing_custom_text_parser")
        self.encoding = self.config.get("encoding", "utf-8")
        self.strip_whitespace = self.config.get("strip_whitespace", True)
        return True

    async def cleanup(self) -> None:
        self.logger.info("cleaning_up_custom_text_parser")

    async def can_parse(self, file_path: str, metadata: Dict[str, Any] = None) -> bool:
        """Check if this parser can handle the given file."""
        path = Path(file_path)
        return path.suffix.lower() in [".txt", ".custom"]

    async def parse(self, file_path: str, **kwargs: Any) -> Dict[str, Any]:
        """Parse the file and return structured data."""
        path = Path(file_path)

        with open(path, "r", encoding=self.encoding) as f:
            content = f.read()

        if self.strip_whitespace:
            content = content.strip()

        # Return a mock parsing result
        return {
            "success": True,
            "content": content,
            "metadata": {
                "parser": "custom_text_parser",
                "file_size": len(content),
                "encoding": self.encoding,
            },
        }

    @property
    def supported_extensions(self) -> List[str]:
        return [".txt", ".custom"]


# Example Custom Chunker Plugin
class CustomChunker(ChunkerPlugin):
    """Example custom chunker plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom_chunker",
            version="1.0.0",
            description="Custom chunking strategy",
            author="Demo Author",
            category="chunker",
            config_schema={
                "chunk_size": {
                    "type": int,
                    "required": False,
                    "default": 500,
                    "description": "Target chunk size in characters",
                },
                "overlap": {
                    "type": int,
                    "required": False,
                    "default": 50,
                    "description": "Overlap between chunks",
                },
            },
        )

    async def initialize(self) -> bool:
        self.logger.info("initializing_custom_chunker")
        self.chunk_size = self.config.get("chunk_size", 500)
        self.overlap = self.config.get("overlap", 50)
        return True

    async def cleanup(self) -> None:
        self.logger.info("cleaning_up_custom_chunker")

    async def chunk(self, document: Any, **kwargs: Any) -> Dict[str, Any]:
        """Chunk the document using custom strategy."""
        if isinstance(document, dict) and "content" in document:
            text = document["content"]
        else:
            text = str(document)

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_content = text[start:end]

            chunks.append(
                {
                    "content": chunk_content,
                    "chunk_index": chunk_index,
                    "start_char": start,
                    "end_char": end,
                    "char_count": len(chunk_content),
                }
            )

            chunk_index += 1
            start = end - self.overlap

            if start >= len(text):
                break

        return {
            "success": True,
            "chunks": chunks,
            "metadata": {
                "chunker": "custom_chunker",
                "chunk_count": len(chunks),
                "strategy": "custom_overlap",
            },
        }


# Example Custom Output Plugin
class CustomJSONOutput(OutputPlugin):
    """Example custom JSON output plugin."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom_json",
            version="1.0.0",
            description="Custom JSON output format",
            author="Demo Author",
            category="output",
            config_schema={
                "pretty_print": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Whether to pretty print JSON",
                },
                "include_metadata": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Whether to include metadata",
                },
            },
        )

    async def initialize(self) -> bool:
        self.logger.info("initializing_custom_json_output")
        self.pretty_print = self.config.get("pretty_print", True)
        self.include_metadata = self.config.get("include_metadata", True)
        return True

    async def cleanup(self) -> None:
        self.logger.info("cleaning_up_custom_json_output")

    async def write_document(
        self, document: Any, output_path: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Write a single document."""
        import json

        output_data = {"document": document}

        if self.include_metadata:
            output_data["output_metadata"] = {
                "format": "custom_json",
                "pretty_print": self.pretty_print,
                "timestamp": "2024-01-01T00:00:00Z",  # Mock timestamp
            }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            if self.pretty_print:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(output_data, f, ensure_ascii=False)

        return {
            "success": True,
            "output_path": str(path),
            "file_size": path.stat().st_size,
            "format": "custom_json",
        }

    async def write_documents(
        self, documents: List[Any], output_path: str, **kwargs: Any
    ) -> Dict[str, Any]:
        """Write multiple documents."""
        combined_data = {"documents": documents, "count": len(documents)}

        return await self.write_document(combined_data, output_path, **kwargs)

    @property
    def file_extension(self) -> str:
        return ".custom.json"


async def main():
    """Demonstrate the plugin system."""
    print("🔌 Plugin System Demo")
    print("=" * 50)

    # Initialize plugin manager
    plugin_manager = PluginManager()

    print("📋 Registering custom plugins...")

    # Register custom plugins
    success1 = plugin_manager.register_plugin(CustomTextParser)
    success2 = plugin_manager.register_plugin(CustomChunker)
    success3 = plugin_manager.register_plugin(CustomJSONOutput)

    print(f"   Custom Text Parser: {'✅' if success1 else '❌'}")
    print(f"   Custom Chunker: {'✅' if success2 else '❌'}")
    print(f"   Custom JSON Output: {'✅' if success3 else '❌'}")
    print()

    # Show system status
    status = plugin_manager.get_system_status()
    print("📊 Plugin System Status:")
    print(f"   Total plugins: {status['total_plugins']}")
    print(f"   Categories: {', '.join(status['available_categories'])}")
    print()

    # List available plugins
    print("📝 Available Plugins:")
    for plugin_info in plugin_manager.list_available_plugins():
        print(
            f"   • {plugin_info['name']} v{plugin_info['version']} ({plugin_info['category']})"
        )
        print(f"     {plugin_info['description']}")
        print(f"     Author: {plugin_info['author']}")
    print()

    # Initialize plugins with custom configurations
    print("🚀 Initializing plugins...")

    configs = {
        "custom_text_parser": {"encoding": "utf-8", "strip_whitespace": True},
        "custom_chunker": {"chunk_size": 300, "overlap": 30},
        "custom_json": {"pretty_print": True, "include_metadata": True},
    }

    init_results = await plugin_manager.initialize_all_plugins(configs)

    for plugin_name, success in init_results.items():
        print(f"   {plugin_name}: {'✅' if success else '❌'}")
    print()

    # Test plugin functionality
    print("🧪 Testing Plugin Functionality...")

    # Create test file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        test_content = """
This is a test document for demonstrating the plugin system.

The plugin system allows you to extend the data pipelines library with custom parsers, chunkers, and output formats.

You can create plugins for:
- Custom document parsers for specialized formats
- Advanced chunking strategies for specific use cases  
- Custom output formats for different storage systems
- General processors for data transformation

The plugin system provides a flexible architecture for extending functionality without modifying the core library.
        """.strip()
        f.write(test_content)
        test_file = f.name

    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Test parser plugin
            parser = plugin_manager.get_plugin("custom_text_parser")
            if parser:
                print("   🔍 Testing custom parser...")
                can_parse = await parser.can_parse(test_file)
                print(f"      Can parse test file: {can_parse}")

                if can_parse:
                    parse_result = await parser.parse(test_file)
                    print(f"      Parse success: {parse_result['success']}")
                    print(f"      Content length: {len(parse_result['content'])} chars")

            # Test chunker plugin
            chunker = plugin_manager.get_plugin("custom_chunker")
            if chunker and parser:
                print("   ✂️  Testing custom chunker...")
                chunk_result = await chunker.chunk(parse_result)
                print(f"      Chunk success: {chunk_result['success']}")
                print(f"      Number of chunks: {len(chunk_result['chunks'])}")

                # Show sample chunks
                for i, chunk in enumerate(chunk_result["chunks"][:2]):
                    preview = (
                        chunk["content"][:50] + "..."
                        if len(chunk["content"]) > 50
                        else chunk["content"]
                    )
                    print(f"      Chunk {i+1}: {repr(preview)}")

            # Test output plugin
            output_plugin = plugin_manager.get_plugin("custom_json")
            if output_plugin and chunker:
                print("   💾 Testing custom output...")
                output_path = Path(temp_dir) / "test_output.custom.json"

                output_result = await output_plugin.write_document(
                    chunk_result, str(output_path)
                )

                print(f"      Output success: {output_result['success']}")
                print(f"      Output file: {output_result['output_path']}")
                print(f"      File size: {output_result['file_size']} bytes")

                # Show file contents preview
                if Path(output_result["output_path"]).exists():
                    with open(output_result["output_path"], "r") as f:
                        content = f.read()
                        preview = (
                            content[:200] + "..." if len(content) > 200 else content
                        )
                        print(f"      Content preview: {repr(preview)}")

            print()

            # Test plugin discovery
            print("🔍 Plugin Discovery Features:")

            # Find suitable parser
            suitable_parser = await plugin_manager.find_suitable_parser(test_file)
            if suitable_parser:
                print(f"   Found suitable parser: {suitable_parser.metadata.name}")

            # Find chunker by strategy
            custom_chunker = plugin_manager.find_chunker_by_strategy("custom_chunker")
            if custom_chunker:
                print(f"   Found chunker by strategy: {custom_chunker.strategy_name}")

            # Find output by format
            json_output = plugin_manager.find_output_by_format("custom_json")
            if json_output:
                print(f"   Found output format: {json_output.format_name}")

            print()

            # Show plugin categories
            print("📂 Plugins by Category:")
            parsers = plugin_manager.get_parser_plugins()
            chunkers = plugin_manager.get_chunker_plugins()
            outputs = plugin_manager.get_output_plugins()

            print(f"   Parsers: {[p.metadata.name for p in parsers]}")
            print(f"   Chunkers: {[c.metadata.name for c in chunkers]}")
            print(f"   Outputs: {[o.metadata.name for o in outputs]}")
            print()

            # Create plugin template
            print("📝 Creating Plugin Template...")
            template_path = Path(temp_dir) / "example_plugin.py"
            template_created = plugin_manager.create_plugin_template(
                template_path,
                plugin_name="example_processor",
                plugin_category="processor",
                author="Demo User",
            )

            if template_created:
                print(f"   ✅ Template created: {template_path}")
                with open(template_path, "r") as f:
                    lines = f.readlines()
                    print(f"   Template has {len(lines)} lines")
                    print("   First few lines:")
                    for line in lines[:5]:
                        print(f"      {line.rstrip()}")

            print()

        finally:
            # Cleanup
            Path(test_file).unlink(missing_ok=True)

            # Cleanup plugins
            print("🧹 Cleaning up plugins...")
            cleanup_results = await plugin_manager.cleanup_all_plugins()

            for plugin_name, success in cleanup_results.items():
                print(f"   {plugin_name}: {'✅' if success else '❌'}")

    print()
    print("🎯 Plugin System Benefits:")
    print("   • Extensible architecture without core modifications")
    print("   • Type-safe plugin interfaces")
    print("   • Automatic plugin discovery and registration")
    print("   • Configuration validation and management")
    print("   • Plugin lifecycle management (init/cleanup)")
    print("   • Template generation for rapid development")


if __name__ == "__main__":
    asyncio.run(main())
