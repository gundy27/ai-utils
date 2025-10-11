"""Base tool registry for OpenAI function calling."""

import structlog
from typing import Any, Callable, Dict, List
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class Tool(BaseModel):
    """Tool definition for OpenAI function calling."""

    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]

    class Config:
        arbitrary_types_allowed = True  # Allow Callable type


class ToolRegistry:
    """Registry for managing OpenAI function calling tools.

    Example:
        registry = ToolRegistry()
        registry.register(CALENDLY_TOOL)

        # Get OpenAI function schemas
        schemas = registry.get_tool_schemas()

        # Execute a tool
        result = registry.execute("schedule_meeting", {"meeting_type": "intro_call"})
    """

    def __init__(self):
        """Initialize tool registry."""
        self.tools: Dict[str, Tool] = {}
        logger.info("tool_registry_initialized")

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Args:
            tool: Tool to register
        """
        if tool.name in self.tools:
            logger.warning("tool_already_registered", tool_name=tool.name)
            return

        self.tools[tool.name] = tool
        logger.info("tool_registered", tool_name=tool.name)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI function schemas for all registered tools.

        Returns:
            List of tool schemas in OpenAI function calling format
        """
        schemas = []
        for tool in self.tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
            )
        return schemas

    def execute(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool by name.

        Args:
            tool_name: Name of tool to execute
            args: Tool arguments from OpenAI

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
        """
        if tool_name not in self.tools:
            logger.error("tool_not_found", tool_name=tool_name)
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        tool = self.tools[tool_name]

        logger.info("tool_executing", tool_name=tool_name, args=args)

        try:
            result = tool.handler(args)
            logger.info("tool_executed", tool_name=tool_name, success=True)
            return result
        except Exception as e:
            logger.error("tool_execution_failed", tool_name=tool_name, error=str(e))
            raise

    def list_tools(self) -> List[str]:
        """Get list of registered tool names.

        Returns:
            List of tool names
        """
        return list(self.tools.keys())
