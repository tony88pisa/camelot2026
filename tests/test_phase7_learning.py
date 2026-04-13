# tests/test_phase7_learning.py
# 2026-04-14 - Phase 7 Certification Suite

import pytest
import time
from ai_trader.risk.opportunity_models import (
    OpportunityCandidate,
    ArbiterDecision,
    QualityScore,
    StructuredRejectedTrade,
)
from ai_trader.risk.portfolio_router import PortfolioRouter
from ai_trader.risk.outcome_evaluator import OutcomeEvaluator


@pytest.fixture
def router():
    return PortfolioRouter()


@pytest.fixture
def evaluator():
    return OutcomeEvaluator(review_window_seconds=3600)


class TestPhase7Learning:
    def test_routing_priority_btc_vs_eth(self, router):
        """ETH con net edge maggiore deve vincere il routing su BTC."""
        dec_btc = ArbiterDecision(
            allowed=True,
            candidate=OpportunityCandidate(
                "BTCUSDT", "BUY", 60000, 0.02, 1.0, "TRENDING", 0.5, "grid_apex"
            ),
            friction=None,
            net_edge_pct=0.018,
            quality=QualityScore.ALPHA,
        )
        dec_eth = ArbiterDecision(
            allowed=True,
            candidate=OpportunityCandidate(
                "ETHUSDT", "BUY", 3000, 0.03, 1.0, "TRENDING", 0.5, "grid_apex"
            ),
            friction=None,
            net_edge_pct=0.028,
            quality=QualityScore.ALPHA,
        )
        winners = router.route([dec_btc, dec_eth])
        assert len(winners) == 1
        assert winners[0].candidate.symbol == "ETHUSDT"

    def test_outcome_evaluation_correct_rejection(self, evaluator):
        """Rejection con move netto <= threshold deve essere classificata come corretta."""
        record = StructuredRejectedTrade(
            symbol="BTCUSDT",
            side="BUY",
            timestamp=time.time() - 3600,
            entry_price=100.0,
            expected_edge_pct=0.01,
            friction_total_pct=0.0003,
            rejection_reason="LOW_EDGE",
            quality="REJECTED",
            signal_strength=1.0,
            regime="TRENDING",
            threshold_used=0.002,
        )
        outcome = evaluator.evaluate_rejection(record, 100.1)
        assert outcome.is_correct_rejection is True
        assert outcome.symbol == "BTCUSDT"
