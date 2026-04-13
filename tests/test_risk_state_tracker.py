# tests/test_risk_state_tracker.py
import pytest
from ai_trader.risk.risk_state_tracker import RiskStateTracker

@pytest.fixture
def tracker():
    t = RiskStateTracker()
    t.initialize_from_summary({"total_balance": 1000.0, "total_exposure": 0.0})
    return t

class TestRiskStateTracker:

    def test_initialization(self, tracker):
        """Verifica lo stato iniziale dopo il boot."""
        assert tracker.session_start_balance == 1000.0
        assert tracker.current_wallet_value == 1000.0
        assert tracker.current_total_exposure == 0.0
        assert tracker.consecutive_losses == 0

    def test_order_fill_buy(self, tracker):
        """Aggiornamento esposizione dopo un BUY."""
        tracker.record_order_fill("BTCUSDT", "BUY", 100.0, 0.001)
        assert tracker.current_total_exposure == 100.0
        assert tracker.per_symbol_exposure["BTCUSDT"] == 100.0

    def test_consecutive_errors(self, tracker):
        """Streak degli errori tecnici."""
        tracker.record_order_failure()
        tracker.record_order_failure()
        assert tracker.consecutive_errors == 2
        # Un fill deve resettare gli errori
        tracker.record_order_fill("BTCUSDT", "BUY", 50.0, 0.0005)
        assert tracker.consecutive_errors == 0

    def test_drawdown_calculation(self, tracker):
        """Calcolo del drawdown stimato."""
        # Perdita di 50 su 1000 = 5%
        tracker.record_loss(-50.0)
        assert tracker.consecutive_losses == 1
        assert tracker.estimated_daily_drawdown_pct == 0.05
        
        # Un'altra perdita
        tracker.record_loss(-50.0)
        assert tracker.consecutive_losses == 2
        assert tracker.estimated_daily_drawdown_pct == 0.10 # 100/1000
        
        # Un guadagno resetta la streak ma non il record di balance iniziale
        tracker.record_gain(20.0)
        assert tracker.consecutive_losses == 0
        # Equity ora 920. Drawdown rispetto a 1000  8%
        assert tracker.estimated_daily_drawdown_pct == 0.08
