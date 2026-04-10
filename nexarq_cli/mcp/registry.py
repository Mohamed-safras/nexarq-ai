"""MCP server registry – register, enable, disable servers (MCP-1)."""
from __future__ import annotations

from nexarq_cli.config.schema import MCPServerConfig, NexarqConfig


class MCPRegistry:
    """Manages registered MCP servers from configuration (MCP-1/2)."""

    def __init__(self, config: NexarqConfig) -> None:
        self._config = config

    def list_servers(self) -> list[MCPServerConfig]:
        return [s for s in self._config.mcp_servers if s.enabled]

    def get_server(self, name: str) -> MCPServerConfig | None:
        for s in self._config.mcp_servers:
            if s.name == name:
                return s
        return None

    def get_local_servers(self) -> list[MCPServerConfig]:
        return [s for s in self.list_servers() if s.local]

    def get_remote_servers(self) -> list[MCPServerConfig]:
        """Remote servers require explicit consent (MCP-5, SEC-8)."""
        return [
            s for s in self.list_servers()
            if not s.local and s.consent_given
        ]

    def register(self, server: MCPServerConfig) -> None:
        """Add a new MCP server. Requires consent for remote servers."""
        if not server.local and not server.consent_given:
            raise PermissionError(
                f"Remote MCP server '{server.name}' requires explicit consent. "
                f"Set consent_given=true in the server config."
            )
        # Remove existing registration with same name
        self._config.mcp_servers = [
            s for s in self._config.mcp_servers if s.name != server.name
        ]
        self._config.mcp_servers.append(server)

    def unregister(self, name: str) -> bool:
        before = len(self._config.mcp_servers)
        self._config.mcp_servers = [
            s for s in self._config.mcp_servers if s.name != name
        ]
        return len(self._config.mcp_servers) < before
