# src/ai_trader/execution/order_models.py
# 2026-04-03 01:35 - Modelli per Execution Policy Engine
"""
Dataclasses usati per convertire l'intent del Signal (Strategy) in un builder di Paper Order,
una volta esibito e superato il gateway di Risk Guardrail.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ai_trader.risk.policy_models import SystemState, MarketState


class ReasonCode(str, Enum):
    """Reason core execution logic limit codes (# 2026-04-03)."""
    PREVIEW_APPROVED = "PREVIEW_APPROVED"
    PREVIEW_BLOCKED_BY_GUARDRAIL = "PREVIEW_BLOCKED_BY_GUARDRAIL"
    PREVIEW_INVALID_INPUT = "PREVIEW_INVALID_INPUT"
    MISSING_REFERENCE_PRICE = "MISSING_REFERENCE_PRICE"
    MISSING_NOTIONAL_AND_QUANTITY = "MISSING_NOTIONAL_AND_QUANTITY"
    INSUFFICIENT_WALLET = "INSUFFICIENT_WALLET"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    INVALID_SYMBOL = "INVALID_SYMBOL"
    INVALID_SIDE = "INVALID_SIDE"


@dataclass
class PaperOrderRequest:
    """Configurazione rigida che mappa un ordine ghost. # 2026-04-03"""
    symbol: str
    side: str
    order_type: str  # es: "PAPER_MARKET"
    proposed_notional: float
    proposed_quantity: float
    reference_price: float
    estimated_cost: float
    regime: str
    signal_quality: float
    source_agent: str
    thesis: str
    timestamp: str  # ISO Format Date


@dataclass
class ExecutionContext:
    """Aggregato info crudo ricevuto dall'esterno sul wallet system."""
    wallet_value: float
    free_quote_balance: float
    open_positions_count: int
    current_total_exposure: float
    per_symbol_exposure: dict[str, float]
    
    system_state: SystemState
    market_state: MarketState


@dataclass
class ExecutionPreviewDecision:
    """Output JSON del process di execution order builder, passabile poi live."""
    ok: bool
    status: str  # "approved_preview" | "blocked" | "invalid"
    guardrail_allowed: bool
    reason_codes: list[str]
    paper_order: dict[str, Any]
    risk_decision: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "guardrail_allowed": self.guardrail_allowed,
            "reason_codes": self.reason_codes,
            "paper_order": self.paper_order,
            "risk_decision": self.risk_decision,
            "error": self.error
        }
