"""Plugin loader for discovering and loading plugins."""

import importlib
import importlib.util
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, List, Type

import structlog

from .base import PluginBase
from .registry import PluginRegistry

logger = structlog.get_logger(__name__)


class PluginLoader:
    """Loader for discovering and loading plugins."""

    def __init__(self, registry: PluginRegistry):
        """Initialize plugin loader.

        Args:
            registry: Plugin registry to register discovered plugins
        """
        self.registry = registry
        self.logger = logger.bind(component="plugin_loader")

    def load_from_directory(self, directory: str | Path, recursive: bool = True) -> int:
        """Load plugins from a directory.

        Args:
            directory: Directory to search for plugins
            recursive: Whether to search subdirectories

        Returns:
            Number of plugins loaded
        """
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            self.logger.warning("plugin_directory_not_found", directory=str(directory))
            return 0

        loaded_count = 0

        # Find Python files
        pattern = "**/*.py" if recursive else "*.py"
        python_files = directory.glob(pattern)

        for file_path in python_files:
            if file_path.name.startswith("__"):
                continue  # Skip __init__.py and __pycache__

            try:
                plugins = self._load_from_file(file_path)
                loaded_count += len(plugins)

                if plugins:
                    self.logger.info(
                        "plugins_loaded_from_file",
                        file=str(file_path),
                        count=len(plugins),
                    )

            except Exception as e:
                self.logger.error(
                    "plugin_file_load_error", file=str(file_path), error=str(e)
                )

        return loaded_count

    def load_from_module(self, module_name: str) -> int:
        """Load plugins from a Python module.

        Args:
            module_name: Name of the module to load

        Returns:
            Number of plugins loaded
        """
        try:
            module = importlib.import_module(module_name)
            plugins = self._discover_plugins_in_module(module)

            loaded_count = 0
            for plugin_class in plugins:
                if self.registry.register(plugin_class):
                    loaded_count += 1

            if loaded_count > 0:
                self.logger.info(
                    "plugins_loaded_from_module", module=module_name, count=loaded_count
                )

            return loaded_count

        except ImportError as e:
            self.logger.error("module_import_error", module=module_name, error=str(e))
            return 0
        except Exception as e:
            self.logger.error("module_load_error", module=module_name, error=str(e))
            return 0

    def load_from_package(self, package_name: str) -> int:
        """Load plugins from a Python package.

        Args:
            package_name: Name of the package to load

        Returns:
            Number of plugins loaded
        """
        try:
            package = importlib.import_module(package_name)

            # Check if package has a plugin discovery function
            if hasattr(package, "get_plugins"):
                plugin_classes = package.get_plugins()
                loaded_count = 0

                for plugin_class in plugin_classes:
                    if self._is_plugin_class(plugin_class):
                        if self.registry.register(plugin_class):
                            loaded_count += 1

                return loaded_count

            # Otherwise, discover plugins in the package
            return self.load_from_module(package_name)

        except Exception as e:
            self.logger.error("package_load_error", package=package_name, error=str(e))
            return 0

    def register_plugin_class(
        self, plugin_class: Type[PluginBase], config: Dict[str, Any] = None
    ) -> bool:
        """Register a plugin class directly.

        Args:
            plugin_class: Plugin class to register
            config: Optional configuration

        Returns:
            True if registration was successful
        """
        if not self._is_plugin_class(plugin_class):
            self.logger.error("invalid_plugin_class", class_name=plugin_class.__name__)
            return False

        return self.registry.register(plugin_class, config)

    def _load_from_file(self, file_path: Path) -> List[Type[PluginBase]]:
        """Load plugins from a Python file."""
        # Create module name from file path
        module_name = f"plugin_{file_path.stem}_{id(file_path)}"

        # Load module from file
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if not spec or not spec.loader:
            raise ImportError(f"Could not load spec from {file_path}")

        module = importlib.util.module_from_spec(spec)

        # Add to sys.modules temporarily
        sys.modules[module_name] = module

        try:
            spec.loader.exec_module(module)
            plugins = self._discover_plugins_in_module(module)

            # Register discovered plugins
            loaded_plugins = []
            for plugin_class in plugins:
                if self.registry.register(plugin_class):
                    loaded_plugins.append(plugin_class)

            return loaded_plugins

        finally:
            # Clean up sys.modules
            if module_name in sys.modules:
                del sys.modules[module_name]

    def _discover_plugins_in_module(self, module) -> List[Type[PluginBase]]:
        """Discover plugin classes in a module."""
        plugins = []

        for name, obj in inspect.getmembers(module):
            if self._is_plugin_class(obj):
                plugins.append(obj)

        return plugins

    def _is_plugin_class(self, obj) -> bool:
        """Check if an object is a valid plugin class."""
        return (
            inspect.isclass(obj)
            and issubclass(obj, PluginBase)
            and obj is not PluginBase
            and not inspect.isabstract(obj)
        )

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
        try:
            template = self._generate_plugin_template(
                plugin_name, plugin_category, author
            )

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(template)

            self.logger.info(
                "plugin_template_created",
                path=str(output_path),
                name=plugin_name,
                category=plugin_category,
            )

            return True

        except Exception as e:
            self.logger.error(
                "plugin_template_creation_error", path=str(output_path), error=str(e)
            )
            return False

    def _generate_plugin_template(
        self, plugin_name: str, category: str, author: str
    ) -> str:
        """Generate plugin template code."""
        class_name = f"{plugin_name.replace('_', ' ').title().replace(' ', '')}Plugin"

        if category == "parser":
            base_class = "ParserPlugin"
            additional_methods = '''
    async def can_parse(self, file_path: str, metadata: Dict[str, Any] = None) -> bool:
        """Check if this parser can handle the given file."""
        # Implement your logic here
        return False
    
    async def parse(self, file_path: str, **kwargs: Any) -> Any:
        """Parse the file and return a PDFParsingResult or similar."""
        # Implement your parsing logic here
        pass
    
    @property
    def supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return [".example"]
'''
        elif category == "chunker":
            base_class = "ChunkerPlugin"
            additional_methods = '''
    async def chunk(self, document: Any, **kwargs: Any) -> Any:
        """Chunk the document and return a ChunkingResult."""
        # Implement your chunking logic here
        pass
    
    @property
    def strategy_name(self) -> str:
        """Get the name of this chunking strategy."""
        return self.metadata.name
'''
        elif category == "output":
            base_class = "OutputPlugin"
            additional_methods = '''
    async def write_document(self, document: Any, output_path: str, **kwargs: Any) -> Any:
        """Write a single document."""
        # Implement your output logic here
        pass
    
    async def write_documents(self, documents: List[Any], output_path: str, **kwargs: Any) -> Any:
        """Write multiple documents."""
        # Implement your batch output logic here
        pass
    
    @property
    def format_name(self) -> str:
        """Get the name of this output format."""
        return self.metadata.name
    
    @property
    def file_extension(self) -> str:
        """Get the file extension for this format."""
        return f".{self.metadata.name.lower()}"
'''
        else:  # processor
            base_class = "ProcessorPlugin"
            additional_methods = '''
    async def process(self, input_data: Any, **kwargs: Any) -> Any:
        """Process the input data."""
        # Implement your processing logic here
        pass
    
    @property
    def processor_type(self) -> str:
        """Get the type of processor."""
        return self.metadata.name
'''

        template = f'''"""
{plugin_name} plugin for data pipelines.

This is a template plugin. Modify it to implement your specific functionality.
"""

from typing import Any, Dict, List
from gundy_ai.data_pipelines.plugins import {base_class}, PluginMetadata


class {class_name}({base_class}):
    """Example {category} plugin."""
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return PluginMetadata(
            name="{plugin_name}",
            version="1.0.0",
            description="Description of {plugin_name} plugin",
            author="{author}",
            category="{category}",
            dependencies=[],
            config_schema={{
                "example_param": {{
                    "type": str,
                    "required": False,
                    "default": "default_value",
                    "description": "Example configuration parameter"
                }}
            }}
        )
    
    async def initialize(self) -> bool:
        """Initialize the plugin."""
        self.logger.info("initializing_{plugin_name}_plugin")
        
        # Add your initialization logic here
        # Return True if successful, False otherwise
        
        return True
    
    async def cleanup(self) -> None:
        """Clean up plugin resources."""
        self.logger.info("cleaning_up_{plugin_name}_plugin")
        
        # Add your cleanup logic here
        pass
{additional_methods}


# Plugin discovery function (optional)
def get_plugins():
    """Return list of plugin classes in this module."""
    return [{class_name}]
'''

        return template
