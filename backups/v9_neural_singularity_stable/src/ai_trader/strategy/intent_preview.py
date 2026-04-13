# src/ai_trader/strategy/intent_preview.py
# 2026-04-03 01:25 - Proxy logico per Guardrail Compatibility
"""
Servizio di conversione che trasforma una StrategyDecision approvata
in un TradeIntent strutturato richiesto dal layer di Rischio.
"""

from typing import Any
from datetime import datetime, timezone
from ai_trader.strategy.policy_models import StrategyDecision

# Hardcode una size dummy molto piccola sicura fino a quando non avremo
# il sub-module di Advanced Position Sizing.
DEFAULT_PROPOSED_NOTIONAL = 50.0  


def build_trade_intent_preview(decision: StrategyDecision, price: float = 0.0) -> dict[str, Any]:
    """
    Costruisce il dict compatibile con il dataclass TradeIntent del Modulo 08 (Risk).
    # 2026-04-03 01:25
    """
    if decision.action != "BUY" or decision.status != "buy_candidate":
        return {}

    proposed_quantity = 0.0
    if price > 0:
        proposed_quantity = DEFAULT_PROPOSED_NOTIONAL / price

    return {
        "symbol": decision.normalized_symbol,
        "side": "BUY",
        "proposed_notional": DEFAULT_PROPOSED_NOTIONAL,
        "proposed_quantity": proposed_quantity,
        "signal_quality": decision.signal_quality,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "regime": "generated_by_strategy",
        "volatility_score": decision.volatility_score,
        "source_agent": "strategy_policy_engine",
        "thesis": decision.thesis
    }
