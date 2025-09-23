"""Plugin manager for coordinating plugin operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from .base import PluginBase, ChunkerPlugin, OutputPlugin, ParserPlugin, ProcessorPlugin
from .loader import PluginLoader
from .registry import PluginRegistry

logger = structlog.get_logger(__name__)


class PluginManager:
    """Manager for coordinating plugin operations."""

    def __init__(self):
        """Initialize plugin manager."""
        self.registry = PluginRegistry()
        self.loader = PluginLoader(self.registry)
        self.logger = logger.bind(component="plugin_manager")

    # Plugin Discovery and Loading

    def discover_plugins(self, search_paths: List[str | Path]) -> int:
        """Discover plugins in multiple search paths.

        Args:
            search_paths: List of directories to search for plugins

        Returns:
            Total number of plugins discovered and loaded
        """
        total_loaded = 0

        for path in search_paths:
            try:
                loaded = self.loader.load_from_directory(path, recursive=True)
                total_loaded += loaded

                if loaded > 0:
                    self.logger.info("plugins_discovered", path=str(path), count=loaded)

            except Exception as e:
                self.logger.error(
                    "plugin_discovery_error", path=str(path), error=str(e)
                )

        return total_loaded

    def load_plugin_module(self, module_name: str) -> bool:
        """Load plugins from a specific module.

        Args:
            module_name: Name of the module to load

        Returns:
            True if any plugins were loaded
        """
        loaded_count = self.loader.load_from_module(module_name)
        return loaded_count > 0

    def register_plugin(
        self, plugin_class: type, config: Dict[str, Any] = None
    ) -> bool:
        """Register a plugin class directly.

        Args:
            plugin_class: Plugin class to register
            config: Optional configuration

        Returns:
            True if registration was successful
        """
        return self.loader.register_plugin_class(plugin_class, config)

    # Plugin Management

    async def initialize_plugin(self, name: str, config: Dict[str, Any] = None) -> bool:
        """Initialize a plugin.

        Args:
            name: Plugin name
            config: Configuration for the plugin

        Returns:
            True if initialization was successful
        """
        return await self.registry.initialize_plugin(name, config)

    async def initialize_all_plugins(
        self, configs: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """Initialize all registered plugins.

        Args:
            configs: Dictionary mapping plugin names to their configurations

        Returns:
            Dictionary mapping plugin names to initialization success status
        """
        configs = configs or {}
        results = {}

        for plugin_info in self.registry.list_plugins():
            plugin_config = configs.get(plugin_info.name, {})
            success = await self.initialize_plugin(plugin_info.name, plugin_config)
            results[plugin_info.name] = success

        return results

    async def cleanup_plugin(self, name: str) -> bool:
        """Cleanup a plugin.

        Args:
            name: Plugin name

        Returns:
            True if cleanup was successful
        """
        return await self.registry.cleanup_plugin(name)

    async def cleanup_all_plugins(self) -> Dict[str, bool]:
        """Cleanup all initialized plugins.

        Returns:
            Dictionary mapping plugin names to cleanup success status
        """
        results = {}

        for plugin_info in self.registry.list_plugins():
            if plugin_info.is_initialized:
                success = await self.cleanup_plugin(plugin_info.name)
                results[plugin_info.name] = success

        return results

    # Plugin Querying

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get an initialized plugin instance by name.

        Args:
            name: Plugin name

        Returns:
            Plugin instance if found and initialized, None otherwise
        """
        plugin_info = self.registry.get_plugin(name)
        if plugin_info and plugin_info.is_initialized:
            return plugin_info.instance
        return None

    def get_plugins_by_category(self, category: str) -> List[PluginBase]:
        """Get all initialized plugins in a category.

        Args:
            category: Plugin category

        Returns:
            List of initialized plugin instances
        """
        plugin_infos = self.registry.get_plugins_by_category(category)
        return [
            info.instance
            for info in plugin_infos
            if info.is_initialized and info.instance
        ]

    def get_parser_plugins(self) -> List[ParserPlugin]:
        """Get all initialized parser plugins."""
        return [
            plugin
            for plugin in self.get_plugins_by_category("parser")
            if isinstance(plugin, ParserPlugin)
        ]

    def get_chunker_plugins(self) -> List[ChunkerPlugin]:
        """Get all initialized chunker plugins."""
        return [
            plugin
            for plugin in self.get_plugins_by_category("chunker")
            if isinstance(plugin, ChunkerPlugin)
        ]

    def get_output_plugins(self) -> List[OutputPlugin]:
        """Get all initialized output plugins."""
        return [
            plugin
            for plugin in self.get_plugins_by_category("output")
            if isinstance(plugin, OutputPlugin)
        ]

    def get_processor_plugins(self) -> List[ProcessorPlugin]:
        """Get all initialized processor plugins."""
        return [
            plugin
            for plugin in self.get_plugins_by_category("processor")
            if isinstance(plugin, ProcessorPlugin)
        ]

    # Plugin Selection

    async def find_suitable_parser(
        self, file_path: str, metadata: Dict[str, Any] = None
    ) -> Optional[ParserPlugin]:
        """Find a suitable parser plugin for a file.

        Args:
            file_path: Path to the file to parse
            metadata: Optional metadata about the file

        Returns:
            Suitable parser plugin or None if none found
        """
        parsers = self.get_parser_plugins()

        for parser in parsers:
            try:
                if await parser.can_parse(file_path, metadata):
                    return parser
            except Exception as e:
                self.logger.warning(
                    "parser_check_error",
                    parser=parser.metadata.name,
                    file_path=file_path,
                    error=str(e),
                )

        return None

    def find_chunker_by_strategy(self, strategy_name: str) -> Optional[ChunkerPlugin]:
        """Find a chunker plugin by strategy name.

        Args:
            strategy_name: Name of the chunking strategy

        Returns:
            Chunker plugin or None if not found
        """
        chunkers = self.get_chunker_plugins()

        for chunker in chunkers:
            if chunker.strategy_name == strategy_name:
                return chunker

        return None

    def find_output_by_format(self, format_name: str) -> Optional[OutputPlugin]:
        """Find an output plugin by format name.

        Args:
            format_name: Name of the output format

        Returns:
            Output plugin or None if not found
        """
        outputs = self.get_output_plugins()

        for output in outputs:
            if output.format_name == format_name:
                return output

        return None

    # Plugin Information

    def list_available_plugins(self) -> List[Dict[str, Any]]:
        """Get information about all available plugins.

        Returns:
            List of plugin information dictionaries
        """
        return [
            self.registry.get_plugin_status(info.name)
            for info in self.registry.list_plugins()
        ]

    def get_plugin_info(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a plugin.

        Args:
            name: Plugin name

        Returns:
            Plugin information dictionary
        """
        return self.registry.get_plugin_status(name)

    def get_system_status(self) -> Dict[str, Any]:
        """Get overall plugin system status.

        Returns:
            System status information
        """
        all_plugins = self.registry.list_plugins()
        initialized_plugins = [p for p in all_plugins if p.is_initialized]
        failed_plugins = [p for p in all_plugins if p.initialization_error]

        categories = {}
        for plugin in all_plugins:
            category = plugin.category
            if category not in categories:
                categories[category] = {"total": 0, "initialized": 0, "failed": 0}

            categories[category]["total"] += 1
            if plugin.is_initialized:
                categories[category]["initialized"] += 1
            if plugin.initialization_error:
                categories[category]["failed"] += 1

        return {
            "total_plugins": len(all_plugins),
            "initialized_plugins": len(initialized_plugins),
            "failed_plugins": len(failed_plugins),
            "categories": categories,
            "available_categories": self.registry.list_categories(),
        }

    # Utility Methods

    def create_plugin_template(
        self,
        output_path: str | Path,
        plugin_name: str,
        plugin_category: str = "processor",
        author: str = "Unknown",
    ) -> bool:
        """Create a plugin template file.

        Args:
            output_path: Path where to create the template
            plugin_name: Name of the plugin
            plugin_category: Category of the plugin
            author: Author name

        Returns:
            True if template was created successfully
        """
        return self.loader.create_plugin_template(
            output_path, plugin_name, plugin_category, author
        )

    async def reload_plugin(self, name: str, config: Dict[str, Any] = None) -> bool:
        """Reload a plugin (cleanup and reinitialize).

        Args:
            name: Plugin name
            config: New configuration for the plugin

        Returns:
            True if reload was successful
        """
        # Cleanup existing instance
        await self.cleanup_plugin(name)

        # Reinitialize with new config
        return await self.initialize_plugin(name, config)
