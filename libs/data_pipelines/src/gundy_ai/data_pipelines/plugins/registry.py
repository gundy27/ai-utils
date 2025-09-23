"""Plugin registry for managing registered plugins."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

import structlog

from .base import PluginBase, PluginMetadata

logger = structlog.get_logger(__name__)


@dataclass
class PluginInfo:
    """Information about a registered plugin."""

    plugin_class: Type[PluginBase]
    metadata: PluginMetadata
    instance: Optional[PluginBase] = None
    is_initialized: bool = False
    initialization_error: Optional[str] = None

    @property
    def name(self) -> str:
        """Get plugin name."""
        return self.metadata.name

    @property
    def category(self) -> str:
        """Get plugin category."""
        return self.metadata.category

    @property
    def version(self) -> str:
        """Get plugin version."""
        return self.metadata.version


class PluginRegistry:
    """Registry for managing plugins."""

    def __init__(self):
        """Initialize plugin registry."""
        self.plugins: Dict[str, PluginInfo] = {}
        self.plugins_by_category: Dict[str, List[PluginInfo]] = {}
        self.logger = logger.bind(component="plugin_registry")

    def register(
        self, plugin_class: Type[PluginBase], config: Dict[str, Any] = None
    ) -> bool:
        """Register a plugin class.

        Args:
            plugin_class: The plugin class to register
            config: Optional configuration for the plugin

        Returns:
            True if registration was successful
        """
        try:
            # Create temporary instance to get metadata
            temp_instance = plugin_class(config or {})
            metadata = temp_instance.metadata

            # Validate metadata
            if not self._validate_metadata(metadata):
                return False

            # Check for name conflicts
            if metadata.name in self.plugins:
                existing = self.plugins[metadata.name]
                self.logger.warning(
                    "plugin_name_conflict",
                    name=metadata.name,
                    existing_version=existing.version,
                    new_version=metadata.version,
                )
                # Allow override if new version is higher
                if not self._is_newer_version(metadata.version, existing.version):
                    return False

            # Create plugin info
            plugin_info = PluginInfo(plugin_class=plugin_class, metadata=metadata)

            # Register plugin
            self.plugins[metadata.name] = plugin_info

            # Add to category index
            if metadata.category not in self.plugins_by_category:
                self.plugins_by_category[metadata.category] = []

            # Remove old version from category if exists
            self.plugins_by_category[metadata.category] = [
                p
                for p in self.plugins_by_category[metadata.category]
                if p.name != metadata.name
            ]
            self.plugins_by_category[metadata.category].append(plugin_info)

            self.logger.info(
                "plugin_registered",
                name=metadata.name,
                version=metadata.version,
                category=metadata.category,
                author=metadata.author,
            )

            return True

        except Exception as e:
            self.logger.error(
                "plugin_registration_error",
                plugin_class=plugin_class.__name__,
                error=str(e),
            )
            return False

    def unregister(self, name: str) -> bool:
        """Unregister a plugin by name."""
        if name not in self.plugins:
            return False

        plugin_info = self.plugins[name]

        # Cleanup instance if exists
        if plugin_info.instance:
            try:
                # Note: This would be async in real implementation
                # await plugin_info.instance.cleanup()
                pass
            except Exception as e:
                self.logger.error("plugin_cleanup_error", name=name, error=str(e))

        # Remove from main registry
        del self.plugins[name]

        # Remove from category index
        category = plugin_info.category
        if category in self.plugins_by_category:
            self.plugins_by_category[category] = [
                p for p in self.plugins_by_category[category] if p.name != name
            ]

        self.logger.info("plugin_unregistered", name=name)
        return True

    def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Get plugin info by name."""
        return self.plugins.get(name)

    def get_plugins_by_category(self, category: str) -> List[PluginInfo]:
        """Get all plugins in a category."""
        return self.plugins_by_category.get(category, [])

    def list_plugins(self) -> List[PluginInfo]:
        """Get list of all registered plugins."""
        return list(self.plugins.values())

    def list_categories(self) -> List[str]:
        """Get list of all plugin categories."""
        return list(self.plugins_by_category.keys())

    async def initialize_plugin(self, name: str, config: Dict[str, Any] = None) -> bool:
        """Initialize a plugin instance.

        Args:
            name: Plugin name
            config: Configuration for the plugin instance

        Returns:
            True if initialization was successful
        """
        plugin_info = self.get_plugin(name)
        if not plugin_info:
            self.logger.error("plugin_not_found", name=name)
            return False

        if plugin_info.is_initialized:
            self.logger.warning("plugin_already_initialized", name=name)
            return True

        try:
            # Create instance with config
            instance_config = config or {}
            instance = plugin_info.plugin_class(instance_config)

            # Validate configuration
            if not instance.validate_config(instance_config):
                plugin_info.initialization_error = "Configuration validation failed"
                return False

            # Initialize the plugin
            success = await instance.initialize()

            if success:
                plugin_info.instance = instance
                plugin_info.is_initialized = True
                plugin_info.initialization_error = None

                self.logger.info("plugin_initialized", name=name)
                return True
            else:
                plugin_info.initialization_error = (
                    "Plugin initialization returned False"
                )
                return False

        except Exception as e:
            error_msg = f"Plugin initialization failed: {str(e)}"
            plugin_info.initialization_error = error_msg
            self.logger.error("plugin_initialization_error", name=name, error=str(e))
            return False

    async def cleanup_plugin(self, name: str) -> bool:
        """Cleanup a plugin instance."""
        plugin_info = self.get_plugin(name)
        if not plugin_info or not plugin_info.instance:
            return False

        try:
            await plugin_info.instance.cleanup()
            plugin_info.instance = None
            plugin_info.is_initialized = False
            plugin_info.initialization_error = None

            self.logger.info("plugin_cleaned_up", name=name)
            return True

        except Exception as e:
            self.logger.error("plugin_cleanup_error", name=name, error=str(e))
            return False

    def get_plugin_status(self, name: str) -> Dict[str, Any]:
        """Get status information for a plugin."""
        plugin_info = self.get_plugin(name)
        if not plugin_info:
            return {"exists": False}

        return {
            "exists": True,
            "name": plugin_info.name,
            "version": plugin_info.version,
            "category": plugin_info.category,
            "author": plugin_info.metadata.author,
            "description": plugin_info.metadata.description,
            "is_initialized": plugin_info.is_initialized,
            "initialization_error": plugin_info.initialization_error,
            "dependencies": plugin_info.metadata.dependencies,
            "config_schema": plugin_info.metadata.config_schema,
        }

    def _validate_metadata(self, metadata: PluginMetadata) -> bool:
        """Validate plugin metadata."""
        required_fields = ["name", "version", "description", "author", "category"]

        for field in required_fields:
            if not getattr(metadata, field, None):
                self.logger.error("invalid_metadata", missing_field=field)
                return False

        valid_categories = ["parser", "chunker", "output", "processor"]
        if metadata.category not in valid_categories:
            self.logger.error(
                "invalid_category",
                category=metadata.category,
                valid_categories=valid_categories,
            )
            return False

        return True

    def _is_newer_version(self, new_version: str, existing_version: str) -> bool:
        """Check if new version is newer than existing version."""
        # Simple version comparison - could be enhanced with proper semver
        try:
            new_parts = [int(x) for x in new_version.split(".")]
            existing_parts = [int(x) for x in existing_version.split(".")]

            # Pad shorter version with zeros
            max_len = max(len(new_parts), len(existing_parts))
            new_parts.extend([0] * (max_len - len(new_parts)))
            existing_parts.extend([0] * (max_len - len(existing_parts)))

            return new_parts > existing_parts

        except ValueError:
            # If version parsing fails, allow override
            return True
