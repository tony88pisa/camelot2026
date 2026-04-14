# src/ai_trader/risk/opportunity_arbiter.py
# 2026-04-13 - Phase 6: Opportunity Arbiter (Ranking & Selection)

from typing import List, Optional
from ai_trader.risk.opportunity_models import OpportunityCandidate, ArbiterDecision, FrictionReport, QualityScore

class OpportunityArbiter:
    """Decisore che classifica le opportunit e seleziona le migliori al netto dei costi."""
    
    def __init__(self, min_net_edge_required: float = 0.001):
        # v12.1: Soglia ridotta a 0.1% per small accounts (era 0.2%)
        # Con 123€ equity e fee Binance standard, 0.2% è irraggiungibile
        self.min_net_edge_required = min_net_edge_required

    def evaluate_candidates(self, candidates: List[OpportunityCandidate], friction_reports: List[FrictionReport]) -> ArbiterDecision:
        """
        Valuta una lista di candidati e ritorna il migliore o NO_TRADE.
        """
        if not candidates:
            return ArbiterDecision(allowed=False, reason_codes=["NO_CANDIDATES"])

        scored_candidates = []
        for i, cand in enumerate(candidates):
            fric = friction_reports[i]
            
            if not fric.is_tradable:
                continue

            # Calcolo Edge Netto (Regola Economica Deterministica)
            # Edge Netto = Edge Lordo - (Costi + Buffer)
            net_edge = cand.expected_edge_pct - fric.total_friction_pct
            
            # Determinazione Qualit
            quality = QualityScore.REJECTED
            if net_edge >= 0.01: # >1% netto
                quality = QualityScore.ALPHA
            elif net_edge >= self.min_net_edge_required:
                quality = QualityScore.BETA
            elif net_edge > 0:
                quality = QualityScore.GAMMA

            scored_candidates.append({
                "candidate": cand,
                "friction": fric,
                "net_edge": net_edge,
                "quality": quality,
                "total_score": net_edge * cand.signal_strength # Ranking combinato
            })

        if not scored_candidates:
            return ArbiterDecision(allowed=False, reason_codes=["NO_TRADABLE_CANDIDATES"])

        # Ordinamento per punteggio totale decrescente
        scored_candidates.sort(key=lambda x: x["total_score"], reverse=True)
        best = scored_candidates[0]

        # Validazione finale contro soglia economica
        if best["quality"] == QualityScore.REJECTED or best["net_edge"] < self.min_net_edge_required:
            return ArbiterDecision(
                allowed=False, 
                candidate=best["candidate"],
                friction=best["friction"],
                net_edge_pct=best["net_edge"],
                quality=QualityScore.REJECTED,
                reason_codes=["INSUFFICIENT_NET_EDGE"]
            )

        return ArbiterDecision(
            allowed=True,
            candidate=best["candidate"],
            friction=best["friction"],
            net_edge_pct=best["net_edge"],
            quality=best["quality"],
            reason_codes=["APPROVED"]
        )
