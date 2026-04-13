# src/ai_trader/execution/__init__.py
# 2026-04-03 01:35 - Package aggregatore per Execution Preview
"""
Execution Layer Pipeline proxy.
Convertitore da intent approvato in paper order da execution live o shadow.
Per ora non instrada ordini all'esterno ma funge da safety wrapper finale.
"""

from ai_trader.execution.order_models import (
    PaperOrderRequest,
    ExecutionPreviewDecision,
    ExecutionContext,
    ReasonCode
)
from ai_trader.execution.execution_preview_engine import ExecutionPreviewEngine

__all__ = [
    "PaperOrderRequest",
    "ExecutionPreviewDecision",
    "ExecutionContext",
    "ReasonCode",
    "ExecutionPreviewEngine"
]
