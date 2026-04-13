# tests/test_risk_kernel.py
import pytest
import time
from ai_trader.risk.risk_kernel import RiskKernel
from ai_trader.risk.policy_models import (
    RiskPolicy, TradeIntent, PortfolioState, SystemState, ReasonCode
)

@pytest.fixture
def policy():
    return RiskPolicy(
        max_daily_drawdown_pct=0.03,
        max_consecutive_losses=3,
        max_symbol_exposure_pct=0.20,
        max_total_exposure_pct=0.80,
        whitelist_pairs=["BTCUSDT", "ETHUSDT"]
    )

@pytest.fixture
def kernel(policy):
    return RiskKernel(policy)

@pytest.fixture
def intent():
    return TradeIntent(
        symbol="BTCUSDT",
        side="BUY",
        proposed_notional=100.0,
        proposed_quantity=0.001,
        signal_quality=0.80,
        timestamp=time.time()
    )

@pytest.fixture
def portfolio():
    return PortfolioState(
        wallet_value=1000.0,
        current_total_exposure=0.0,
        open_positions_count=0,
        per_symbol_exposure={}
    )

@pytest.fixture
def system():
    return SystemState(
        consecutive_losses=0,
        consecutive_errors=0,
        daily_drawdown_pct=0.0,
        weekly_drawdown_pct=0.0
    )

class TestRiskKernel:

    def test_allow_healthy_trade(self, kernel, intent, portfolio, system):
        """Un trade sano deve essere approvato."""
        res = kernel.evaluate_intent(intent, portfolio, system)
        assert res.allowed is True
        assert ReasonCode.APPROVED.value in res.reason_codes

    def test_block_daily_drawdown(self, kernel, intent, portfolio, system):
        """Deve bloccare se il drawdown giornaliero  superato."""
        system.daily_drawdown_pct = 0.04 # 4% > 3%
        res = kernel.evaluate_intent(intent, portfolio, system)
        assert res.allowed is False
        assert ReasonCode.DAILY_DRAWDOWN_LIMIT.value in res.reason_codes

    def test_block_consecutive_losses(self, kernel, intent, portfolio, system):
        """Deve bloccare se le perdite consecutive superano la soglia."""
        system.consecutive_losses = 4 # 4 > 3
        res = kernel.evaluate_intent(intent, portfolio, system)
        assert res.allowed is False
        assert ReasonCode.TOO_MANY_CONSECUTIVE_LOSSES.value in res.reason_codes

    def test_block_symbol_exposure(self, kernel, intent, portfolio, system):
        """Deve bloccare se l'esposizione sul singolo simbolo eccede la policy."""
        # wallet 1000. limit 20% = 200. Notional richiesto 300.
        intent.proposed_notional = 300.0
        res = kernel.evaluate_intent(intent, portfolio, system)
        assert res.allowed is False
        assert ReasonCode.SINGLE_POSITION_LIMIT.value in res.reason_codes

    def test_block_total_exposure(self, kernel, intent, portfolio, system):
        """Deve bloccare se l'esposizione totale eccede la policy."""
        # wallet 1000. limit 80% = 800. Notional esistente 750 + richiesto 100 = 850.
        portfolio.current_total_exposure = 750.0
        res = kernel.evaluate_intent(intent, portfolio, system)
        assert res.allowed is False
        assert ReasonCode.TOTAL_EXPOSURE_LIMIT.value in res.reason_codes

    def test_block_kill_switch(self, kernel, intent, portfolio, system, policy):
        """Deve bloccare se il Kill-Switch  attivo."""
        policy.kill_switch_enabled = True
        res = kernel.evaluate_intent(intent, portfolio, system)
        assert res.allowed is False
        assert "KILL_SWITCH" in res.reason_codes[0]

    def test_block_not_whitelisted(self, kernel, intent, portfolio, system):
        """Deve bloccare simboli non in whitelist."""
        intent.symbol = "SHIBUSDT"
        res = kernel.evaluate_intent(intent, portfolio, system)
        assert res.allowed is False
        assert ReasonCode.SYMBOL_NOT_ALLOWED.value in res.reason_codes
