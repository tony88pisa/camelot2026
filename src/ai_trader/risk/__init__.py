# src/ai_trader/risk/__init__.py
# 2026-04-03 01:20 - Inizializzazione package Risk
"""
Risk Guardrail Engine.
Modulo per la sicurezza deterministica delle esecuzioni.
Impedisce ai modelli AI di effettuare trade ad alto rischio o fuori whitelist.
"""

from ai_trader.risk.policy_models import (
    RiskPolicy,
    TradeIntent,
    GuardrailDecision,
    PortfolioState,
    SystemState,
    MarketState,
    ReasonCode
)
from ai_trader.risk.guardrail_engine import GuardrailEngine

__all__ = [
    "RiskPolicy",
    "TradeIntent",
    "GuardrailDecision",
    "PortfolioState",
    "SystemState",
    "MarketState",
    "ReasonCode",
    "GuardrailEngine"
]
