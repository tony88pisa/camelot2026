# src/ai_trader/strategy/policy_models.py
# 2026-04-03 01:25 - Modelli per Strategy Policy Engine
"""
Dataclasses usate dallo Strategy Engine per incapsulare il design logico
della strategy (Input + Configurazione) e la sua determinazione.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReasonCode(str, Enum):
    """Reason core limit codes for Strategy Decisions. # 2026-04-03"""
    SYMBOL_NOT_SUPPORTED = "SYMBOL_NOT_SUPPORTED"
    ADAPTER_UNAVAILABLE = "ADAPTER_UNAVAILABLE"
    MARKET_SNAPSHOT_MISSING = "MARKET_SNAPSHOT_MISSING"
    MEMORY_CONTEXT_MISSING = "MEMORY_CONTEXT_MISSING"
    REGIME_BLOCKED = "REGIME_BLOCKED"
    LOW_SIGNAL_QUALITY = "LOW_SIGNAL_QUALITY"
    LOW_TREND_SCORE = "LOW_TREND_SCORE"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    HOLD_BY_POLICY = "HOLD_BY_POLICY"
    BUY_CANDIDATE = "BUY_CANDIDATE"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"
    INVALID_SIGNAL_INPUT = "INVALID_SIGNAL_INPUT"


@dataclass
class StrategyPolicy:
    """Configurazione strategica limitativa dello scouting. # 2026-04-03"""
    allowed_symbols: list[str] = field(default_factory=lambda: ["DOGEUSDT", "XRPUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT"])
    supported_sides: list[str] = field(default_factory=lambda: ["BUY"])
    
    max_new_entries_per_cycle: int = 1
    
    min_signal_quality: float = 0.65
    min_trend_score: float = 0.50
    max_volatility_score: float = 0.05
    
    require_memory_context: bool = False  # Pu essere False testnet start base
    require_market_snapshot: bool = True
    require_adapter_health: bool = True
    
    allowed_regimes: list[str] = field(default_factory=lambda: ["normal", "bull", "trend_following"])
    blocked_regimes: list[str] = field(default_factory=lambda: ["bear", "forbidden", "high_chop", "uncertain"])
    
    # Placeholder per future implementazioni take profit su intents
    atr_stop_multiplier: float = 1.5
    atr_takeprofit_multiplier: float = 2.0


@dataclass
class SignalInput:
    """Aggregato info crudo ricevuto dall'esterno/tools/model."""
    symbol: str
    price: float
    timestamp: str  # ISO Format Date
    
    normalized_symbol: str = ""
    trend_score: float = 0.0
    momentum_score: float = 0.0
    volatility_score: float = 0.0
    regime: str = "normal"
    signal_quality: float = 0.0
    
    adapter_health: bool = True
    market_snapshot_available: bool = True
    
    memory_summary: str = ""
    recent_lessons_count: int = 0
    recent_episodes_count: int = 0
    
    source_agent: str = "strategy_layer"


@dataclass
class StrategyDecision:
    """Output dell'engine, predisposto per la Dashboard e il Risk module."""
    ok: bool
    status: str  # "buy_candidate" | "hold" | "skip" | "blocked"
    action: str  # "BUY" | "HOLD" | "SKIP"
    normalized_symbol: str
    signal_quality: float
    trend_score: float
    volatility_score: float
    confidence: float
    reason_codes: list[str]
    thesis: str
    intent_preview: dict[str, Any]
    error: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "action": self.action,
            "normalized_symbol": self.normalized_symbol,
            "signal_quality": self.signal_quality,
            "trend_score": self.trend_score,
            "volatility_score": self.volatility_score,
            "confidence": self.confidence,
            "reason_codes": self.reason_codes,
            "thesis": self.thesis,
            "intent_preview": self.intent_preview,
            "error": self.error
        }
