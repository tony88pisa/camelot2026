# src/ai_trader/tools/base_trading_tools.py
# 2026-04-03 00:55 - Modulo per BaseTradingTool
"""
Fornisce la classe BaseTradingTool che estende il framework MCP.
Questa classe introduce marcatori semantici, come controlli ReadOnly.
"""

from typing import Any

from ai_trader.mcp.tool_base import BaseTool


class BaseTradingTool(BaseTool):
    """
    Classe base specifica per i trading tools, estende MCP BaseTool.
    Introduce la proprietà fissa `is_read_only` per differenziare
    l'uso sicuro.
    # 2026-04-03 00:55
    """

    @property
    def is_read_only(self) -> bool:
        """
        Di default i tool sono safe e READ-ONLY. 
        I wrapper live dovranno over-ridare esplicitamente.
        # 2026-04-03 00:55
        """
        return True
