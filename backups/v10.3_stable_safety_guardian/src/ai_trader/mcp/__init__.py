# src/ai_trader/mcp/__init__.py
# 2026-04-02 22:28 - Package MCP Core
"""
MCP (Model Context Protocol) Core.
Gestisce registrazione tool, schema Ollama, e ciclo orchestrazione chat+tools.
"""
from ai_trader.mcp.tool_base import BaseTool  # noqa: F401
from ai_trader.mcp.registry import ToolRegistry  # noqa: F401
from ai_trader.mcp.orchestrator import MCPOrchestrator  # noqa: F401
