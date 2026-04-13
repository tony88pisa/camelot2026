# src/ai_trader/strategy/__init__.py
# 2026-04-03 01:25 - Package aggregatore Modulo Strategy base
"""
Strategy Policy Engine.
Layer iniziale del cervello di trading: riceve segnali di mercato e memoria grezzi,
generando una intenzione formatta JSON (BUY, HOLD, SKIP) adatta
al pre-execution check del Guardrail. Deterministico.
"""

from ai_trader.strategy.policy_models import (
    StrategyPolicy,
    SignalInput,
    StrategyDecision,
    ReasonCode
)
from ai_trader.strategy.intent_preview import build_trade_intent_preview
from ai_trader.strategy.strategy_policy_engine import StrategyPolicyEngine

__all__ = [
    "StrategyPolicy",
    "SignalInput",
    "StrategyDecision",
    "ReasonCode",
    "StrategyPolicyEngine",
    "build_trade_intent_preview"
]
