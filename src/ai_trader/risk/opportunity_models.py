# src/ai_trader/risk/opportunity_models.py
# 2026-04-13 - Phase 6: Shared Economic Models

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum

class QualityScore(Enum):
    ALPHA = "ALPHA"  # Premium quality
    BETA = "BETA"   # Standard quality
    GAMMA = "GAMMA"  # Low quality
    REJECTED = "REJECTED"

@dataclass
class FrictionReport:
    """Rapporto deterministico sui costi di transazione stimati."""
    symbol: str
    fee_pct: float = 0.001  # Default conservative 0.1%
    spread_pct: float = 0.0
    slippage_est_pct: float = 0.0
    total_friction_pct: float = 0.0
    is_tradable: bool = True
    reason: Optional[str] = None

@dataclass
class OpportunityCandidate:
    """Rappresentazione unificata di un'opportunit di trading."""
    symbol: str
    side: str  # BUY/SELL
    entry_price: float
    expected_edge_pct: float
    signal_strength: float  # 0.0 to 1.0
    regime: str
    volatility_score: float
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ArbiterDecision:
    """Decisione finale dell'Opportunity Arbiter."""
    allowed: bool
    candidate: Optional[OpportunityCandidate] = None
    friction: Optional[FrictionReport] = None
    net_edge_pct: float = 0.0
    quality: QualityScore = QualityScore.REJECTED
    reason_codes: List[str] = field(default_factory=list)

@dataclass
class AllocationDecision:
    """Decisione finale di dimensionamento capitale."""
    symbol: str
    action: str  # BUY/SELL/NO_TRADE
    allocated_notional: float = 0.0
    reserve_preserved: float = 0.0
    reason: Optional[str] = None

@dataclass
class StructuredRejectedTrade:
    """Record strutturato di un'opportunità scartata per EpisodeStore."""
    symbol: str
    side: str
    timestamp: float
    entry_price: float
    expected_edge_pct: float
    friction_total_pct: float
    rejection_reason: str
    quality: str
    signal_strength: float
    regime: str
    threshold_used: float
    rejection_mode: str = "NO_TRADE"

@dataclass
class CounterfactualOutcome:
    """Esito misurato di una decisione di rifiuto per LessonStore."""
    symbol: str
    occurred_at: float
    evaluated_at: float
    entry_price: float
    exit_price_60m: float
    hypothetical_move_pct: float
    hypothetical_net_return_pct: float
    is_correct_rejection: bool
    rejection_mode: str

@dataclass
class RoutingDecision:
    """Snapshot di una decisione di portfolio routing."""
    timestamp: float
    winner: Optional[ArbiterDecision] = None
    all_candidates: List[ArbiterDecision] = field(default_factory=list)
    reason: str = ""
