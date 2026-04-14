# src/ai_trader/risk/policy_models.py
# 2026-04-03 01:20 - Modelli Dati per Risk Guardrail Engine
"""
Dataclasses definenti le policy in input e the state evaluation context
per impedire accessi/trades che violano rigid-rules.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ReasonCode(str, Enum):
    """Reason core limit codes. # 2026-04-03"""
    SYMBOL_NOT_ALLOWED = "SYMBOL_NOT_ALLOWED"
    ADAPTER_UNHEALTHY = "ADAPTER_UNHEALTHY"
    ACCOUNT_UNAVAILABLE = "ACCOUNT_UNAVAILABLE"
    TOO_MANY_OPEN_TRADES = "TOO_MANY_OPEN_TRADES"
    TOTAL_EXPOSURE_LIMIT = "TOTAL_EXPOSURE_LIMIT"
    SINGLE_POSITION_LIMIT = "SINGLE_POSITION_LIMIT"
    LOW_SIGNAL_QUALITY = "LOW_SIGNAL_QUALITY"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    SYMBOL_COOLDOWN_ACTIVE = "SYMBOL_COOLDOWN_ACTIVE"
    SYSTEM_COOLDOWN_ACTIVE = "SYSTEM_COOLDOWN_ACTIVE"
    DAILY_DRAWDOWN_LIMIT = "DAILY_DRAWDOWN_LIMIT"
    WEEKLY_DRAWDOWN_LIMIT = "WEEKLY_DRAWDOWN_LIMIT"
    TOO_MANY_CONSECUTIVE_ERRORS = "TOO_MANY_CONSECUTIVE_ERRORS"
    TOO_MANY_CONSECUTIVE_LOSSES = "TOO_MANY_CONSECUTIVE_LOSSES"
    MARKET_DATA_MISSING = "MARKET_DATA_MISSING"
    INVALID_SIZE = "INVALID_SIZE"
    APPROVED = "APPROVED"


@dataclass
class RiskPolicy:
    """Configurazione rigida che regola i confini consentiti. # 2026-04-03"""
    # Immutable rules
    allow_short: bool = False
    allow_margin: bool = False
    allow_leverage: bool = False
    live_mode: bool = False
    require_adapter_health: bool = True
    
    # Tolerances & Thresholds (Can be optimized via self-training loop)
    whitelist_pairs: list[str] = field(default_factory=lambda: [
        "PEPEEUR", "BTCEUR", "ETHEUR", "SOLEUR", "BNBEUR",
        "DOGEEUR", "XRPEUR", "ADAEUR", "LINKEUR", "AVAXEUR"
    ])
    max_open_trades: int = 5
    max_total_exposure_pct: float = 0.60  # 60%  budget piccolo richiede pi esposizione
    max_single_position_pct: float = 0.35 # 35%  con 55 USDT, 10% = solo $5.5 (troppo poco)
    max_new_entries_per_cycle: int = 2
    
    # Stop loss / Volatility sizing base
    atr_stop_multiplier: float = 1.5
    atr_takeprofit_multiplier: float = 2.0
    volatility_block_threshold: float = 0.05  # >5% intra-window jump = block
    
    # Limits hard drawdown limits
    max_daily_drawdown_pct: float = 0.03   # 3% loss max daily
    max_weekly_drawdown_pct: float = 0.06
    max_consecutive_losses: int = 3
    max_consecutive_errors: int = 3
    
    # Granular Exposure Limits (Phase 2)
    max_symbol_exposure_pct: float = 0.20 # 20% max per simbolo
    max_total_exposure_pct: float = 0.80  # 80% max portafoglio
    
    # Cooldown setup
    symbol_cooldown_minutes: int = 60
    system_cooldown_minutes: int = 120
    cooldown_after_loss_streak_minutes: int = 240 # 4h pausa se streak negativa
    
    # Kill-Switch
    kill_switch_enabled: bool = False
    
    min_signal_quality: float = 0.60


@dataclass
class TradeIntent:
    """Intenzione logica di Agent prima dell'approvazione del Guardrail."""
    symbol: str
    side: str
    proposed_notional: float
    proposed_quantity: float
    signal_quality: float
    timestamp: float  # Unix timestamp per calcoli cooldown
    
    regime: str = "neutral"
    volatility_score: float = 0.0
    source_agent: str = "unknown"
    thesis: str = ""


@dataclass
class PortfolioState:
    """Context snapshot del wallet per il Risk Kernel."""
    wallet_value: float
    current_total_exposure: float
    open_positions_count: int
    per_symbol_exposure: dict[str, float] # symbol -> notional value


@dataclass
class SystemState:
    """Stato organico del bot tracking health per il Risk Kernel."""
    consecutive_losses: int
    consecutive_errors: int
    daily_drawdown_pct: float
    weekly_drawdown_pct: float
    session_pnl: float = 0.0
    
    system_cooldown_until: float | None = None  # Unix timestamp
    symbol_cooldowns: dict[str, float] = field(default_factory=dict) # Unix timestamps map
    last_risk_block_reason: str | None = None


@dataclass
class MarketState:
    """Rappresentazione base e adapter status per il simbolo corrente."""
    adapter_health: bool
    market_snapshot_available: bool
    normalized_symbol: str
    price: float
    volatility_score: float
    regime: str


@dataclass
class GuardrailDecision:
    """Risultato Json-friendly deterministico della valutazione intento.# 2026-04-03"""
    ok: bool
    allowed: bool
    status: str  # "approved" | "blocked" | "review_required"
    reason_codes: list[str]
    normalized_symbol: str
    approved_notional: float
    risk_snapshot: dict[str, Any]
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "allowed": self.allowed,
            "status": self.status,
            "reason_codes": self.reason_codes,
            "normalized_symbol": self.normalized_symbol,
            "approved_notional": self.approved_notional,
            "risk_snapshot": self.risk_snapshot,
            "error": self.error
        }
