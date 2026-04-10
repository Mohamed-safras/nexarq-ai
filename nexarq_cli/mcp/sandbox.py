"""MCP sandbox – wraps registry + client with unified safe access (MCP-3)."""
from __future__ import annotations

from typing import Any

from nexarq_cli.config.schema import NexarqConfig
from nexarq_cli.mcp.client import MCPClient, MCPToolResult
from nexarq_cli.mcp.registry import MCPRegistry


class MCPSandbox:
    """
    Single entry point for agents to interact with MCP servers safely.

    All calls are:
    - Permission-checked (allowed_tools list)
    - Result-sanitized (injection-safe)
    - Consent-gated for remote servers
    """

    def __init__(self, config: NexarqConfig) -> None:
        self._registry = MCPRegistry(config)
        self._clients: dict[str, MCPClient] = {}

    def call(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> MCPToolResult:
        """Call a tool on a named server."""
        server = self._registry.get_server(server_name)
        if server is None:
            return MCPToolResult(
                tool=tool_name,
                server=server_name,
                data=None,
                error=f"MCP server '{server_name}' not registered or not enabled.",
            )

        if not server.enabled:
            return MCPToolResult(
                tool=tool_name,
                server=server_name,
                data=None,
                error=f"MCP server '{server_name}' is disabled.",
            )

        client = self._get_client(server_name)
        return client.call_tool(tool_name, arguments or {})

    def available_tools(self, server_name: str) -> list[str]:
        server = self._registry.get_server(server_name)
        if server is None:
            return []
        client = self._get_client(server_name)
        tools = client.list_tools()
        # Filter by allowed list if set
        if server.allowed_tools:
            return [t for t in tools if t in server.allowed_tools]
        return tools

    def server_names(self) -> list[str]:
        return [s.name for s in self._registry.list_servers()]

    # ── internal ─────────────────────────────────────────────────────────────

    def _get_client(self, name: str) -> MCPClient:
        if name not in self._clients:
            server = self._registry.get_server(name)
            if server is None:
                raise KeyError(f"Server not found: {name}")
            self._clients[name] = MCPClient(server)
        return self._clients[name]
