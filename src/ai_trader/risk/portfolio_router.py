# src/ai_trader/risk/portfolio_router.py
# 2026-04-14 - Phase 7: Portfolio Router (Multi-Asset Arbitration)

from typing import List, Optional
from ai_trader.risk.opportunity_models import ArbiterDecision, QualityScore


class PortfolioRouter:
    """Classifica e sceglie la migliore opportunita tra BTC e ETH based on net edge."""

    def __init__(self, top_n: int = 1):
        self.top_n = top_n

    def route(self, decisions: List[ArbiterDecision]) -> List[ArbiterDecision]:
        """Seleziona i migliori candidati tra tutte le decisioni di arbitraggio."""
        allowed = [d for d in decisions if d.allowed and d.quality != QualityScore.REJECTED]
        if not allowed:
            return []

        def _score_decision(d: ArbiterDecision) -> float:
            quality_weight = {"ALPHA": 1.5, "BETA": 1.0, "GAMMA": 0.5, "REJECTED": 0.0}
            q_val = quality_weight.get(d.quality.value, 0.0)
            return (d.net_edge_pct * (d.candidate.signal_strength if d.candidate else 1.0)) * q_val

        allowed.sort(key=_score_decision, reverse=True)
        return allowed[:self.top_n]

    def identify_routed_away(
        self, decisions: List[ArbiterDecision], winner: Optional[ArbiterDecision]
    ) -> List[ArbiterDecision]:
        """Identifica candidati validi scartati a favore del vincitore."""
        if not winner or not winner.candidate:
            return []
        return [
            d for d in decisions
            if d.allowed and d.candidate and d.candidate.symbol != winner.candidate.symbol
        ]
