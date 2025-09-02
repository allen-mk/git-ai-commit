from typing import Any, Mapping

from core.contracts.collector import Collector
from core.registry import collector_registry
from utils.logger import logger


@collector_registry.register("mcp")
class MCPCollector(Collector):
    """
    A collector for the MCP protocol.

    TODO: This is a placeholder implementation.
    The actual implementation requires details on the MCP protocol,
    declarative tool call configuration, and client implementation.
    """

    def __init__(self, *args, **kwargs):
        logger.warning(
            "The 'mcp' collector is not fully implemented and will do nothing."
        )

    def collect(self) -> Mapping[str, Any]:
        """
        This is a dummy implementation and will return an empty dictionary.
        """
        # TODO: Implement MCP client logic here.
        # 1. Read declarative tool configuration.
        # 2. Establish connection based on MCP protocol.
        # 3. Execute tool calls.
        # 4. Handle timeouts and errors.
        # 5. Return structured output.
        return {"mcp_data": {}}
