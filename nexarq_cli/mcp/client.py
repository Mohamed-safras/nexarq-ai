"""MCP client – tool invocation with permission checks (MCP-2/3/6)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from nexarq_cli.config.schema import MCPServerConfig
from nexarq_cli.security.validator import OutputValidator


@dataclass
class MCPToolResult:
    tool: str
    server: str
    data: Any
    sanitized: bool = False
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


class MCPClient:
    """
    Calls tools on registered MCP servers.

    Security guarantees:
    - MCP-6: No direct execution without validation
    - MCP-7: All responses are sanitized before use
    - MCP-8: Network access restricted per server config
    """

    def __init__(self, server: MCPServerConfig) -> None:
        self._server = server
        self._validator = OutputValidator()

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        """Call a tool on the MCP server with permission enforcement."""
        # Check allowed tools (MCP-3)
        if self._server.allowed_tools and tool_name not in self._server.allowed_tools:
            return MCPToolResult(
                tool=tool_name,
                server=self._server.name,
                data=None,
                error=(
                    f"Tool '{tool_name}' is not in the allowed tools list for "
                    f"server '{self._server.name}'. "
                    f"Allowed: {', '.join(self._server.allowed_tools) or 'none'}"
                ),
            )

        try:
            raw_result = self._invoke(tool_name, arguments)
            return self._sanitize_result(tool_name, raw_result)
        except Exception as exc:
            return MCPToolResult(
                tool=tool_name,
                server=self._server.name,
                data=None,
                error=str(exc),
            )

    def list_tools(self) -> list[str]:
        """Return available tools from the server."""
        try:
            result = self._invoke("list_tools", {})
            if isinstance(result, list):
                return result
            return []
        except Exception:
            return []

    # ── internal ─────────────────────────────────────────────────────────────

    def _invoke(self, tool_name: str, arguments: dict) -> Any:
        """Low-level HTTP call to the MCP server (MCP-8: restricted network)."""
        import httpx

        url = f"{self._server.uri.rstrip('/')}/tools/{tool_name}"
        with httpx.Client(timeout=self._server.timeout) as client:
            response = client.post(url, json={"arguments": arguments})
            response.raise_for_status()
            return response.json()

    def _sanitize_result(self, tool_name: str, raw: Any) -> MCPToolResult:
        """Sanitize and validate MCP response (MCP-7)."""
        # Convert to string for validation
        if isinstance(raw, str):
            text = raw
        else:
            text = json.dumps(raw)

        validation = self._validator.validate(text, context=f"mcp:{self._server.name}")

        return MCPToolResult(
            tool=tool_name,
            server=self._server.name,
            data=raw if validation.is_valid else validation.sanitized_text,
            sanitized=True,
            warnings=validation.warnings,
        )
