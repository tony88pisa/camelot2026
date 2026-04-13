import pytest
from unittest.mock import MagicMock
from ai_trader.risk.opportunity_models import OpportunityCandidate, QualityScore
from ai_trader.risk.friction_brain import FrictionBrain
from ai_trader.risk.opportunity_arbiter import OpportunityArbiter
from ai_trader.risk.capital_allocator import CapitalAllocator

@pytest.fixture
def friction_brain():
    return FrictionBrain(maker_fee=0.001, taker_fee=0.001)

@pytest.fixture
def arbiter():
    return OpportunityArbiter(min_net_edge_required=0.002)

@pytest.fixture
def allocator():
    return CapitalAllocator(reserve_pct=0.2, max_single_allocation=25.0)

class TestPhase6Allocation:

    def test_friction_brain_calculation(self, friction_brain):
        """Verifica che il costo totale includa fee, spread e buffer."""
        order_book = {
            "bids": [[100.0, 1.0]],
            "asks": [[100.1, 1.0]]
        }
        # Spread = 0.1 / 100.05 = 0.001 (0.1%)
        # Fee = 0.001 (0.1%)
        # Buffer = 0.0005 (0.05%)
        # Total Friction = 0.001 + 0.0005 + 0.0005 = 0.002 (0.2%)
        report = friction_brain.estimate_friction("BTCUSDT", order_book, 10.0)
        assert report.is_tradable is True
        assert report.total_friction_pct >= 0.002

    def test_arbiter_rejection_low_net_edge(self, arbiter):
        """Verifica NO_TRADE se l'edge netto  sotto la soglia."""
        cand = OpportunityCandidate(
            symbol="BTCUSDT", side="BUY", entry_price=100.0,
            expected_edge_pct=0.002, # 0.2% lordo
            signal_strength=1.0, regime="TREND", volatility_score=0.5, source="test"
        )
        fric = MagicMock(total_friction_pct=0.003, is_tradable=True) # Costi 0.3%
        # Net Edge = -0.1% -> REJECTED
        decision = arbiter.evaluate_candidates([cand], [fric])
        assert decision.allowed is False
        assert "INSUFFICIENT_NET_EDGE" in decision.reason_codes

    def test_arbiter_approval_and_ranking(self, arbiter):
        """Verifica che l'opportunit migliore venga selezionata."""
        cand_a = OpportunityCandidate("A", "BUY", 1.0, 0.01, 1.0, "R", 0.1, "S") # 1% edge
        cand_b = OpportunityCandidate("B", "BUY", 1.0, 0.02, 1.0, "R", 0.1, "S") # 2% edge
        
        fric = MagicMock(total_friction_pct=0.002, is_tradable=True)
        decision = arbiter.evaluate_candidates([cand_a, cand_b], [fric, fric])
        
        assert decision.allowed is True
        assert decision.candidate.symbol == "B"
        assert decision.quality == QualityScore.ALPHA

    def test_allocator_preserves_reserve(self, allocator):
        """Verifica che l'allocatore rispetti la riserva di cassa."""
        decision = MagicMock(allowed=True, quality=QualityScore.ALPHA, reason_codes=["APPROVED"])
        decision.candidate.side = "BUY"
        decision.candidate.signal_strength = 1.0
        
        # Saldo 100 USDT. Riserva 20% = 20. Usable = 80.
        # Max single = 25. Allocazione finale dovrebbe essere 25.
        alloc = allocator.allocate(decision, 100.0)
        assert alloc.action == "BUY"
        assert alloc.allocated_notional == 25.0
        assert alloc.reserve_preserved == 20.0

    def test_allocator_too_small_rejection(self, allocator):
        """Verifica NO_TRADE se l'allocazione finale  sotto il limite Binance (10 USDT)."""
        decision = MagicMock(allowed=True, quality=QualityScore.GAMMA, reason_codes=["APPROVED"])
        decision.quality = QualityScore.GAMMA # Moltiplicatore 0.4
        decision.candidate.side = "BUY"
        decision.candidate.signal_strength = 0.5 # Segnale debole
        
        # Saldo 100 USDT. Max 25. 25 * 0.4 * 0.5 = 5.0 USDT.
        # 5.0 < 10.0 -> REJECTED
        alloc = allocator.allocate(decision, 100.0)
        assert alloc.action == "NO_TRADE"
        assert "ALLOCATION_TOO_SMALL" in alloc.reason
