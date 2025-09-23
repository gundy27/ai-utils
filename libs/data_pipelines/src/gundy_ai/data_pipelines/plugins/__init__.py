"""Plugin system for extensible parsers and chunkers."""

from .registry import PluginRegistry, PluginInfo
from .base import PluginBase, ParserPlugin, ChunkerPlugin, OutputPlugin
from .loader import PluginLoader
from .manager import PluginManager

__all__ = [
    "PluginRegistry",
    "PluginInfo",
    "PluginBase",
    "ParserPlugin",
    "ChunkerPlugin",
    "OutputPlugin",
    "PluginLoader",
    "PluginManager",
]
