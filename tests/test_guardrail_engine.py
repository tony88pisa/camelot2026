# tests/test_guardrail_engine.py
# 2026-04-03 01:20 - Suite di validazione Rule check del Guardrail
import pytest
from datetime import datetime, timezone

from ai_trader.risk.policy_models import (
    RiskPolicy,
    TradeIntent,
    GuardrailDecision,
    PortfolioState,
    SystemState,
    MarketState,
    ReasonCode
)
from ai_trader.risk.guardrail_engine import GuardrailEngine


@pytest.fixture
def default_policy():
    return RiskPolicy(
        whitelist_pairs=["BTCUSDT", "ETHUSDT"],
        max_open_trades=3,
        max_total_exposure_pct=0.30,
        max_single_position_pct=0.10,
        min_signal_quality=0.60
    )


@pytest.fixture
def base_intent():
    return TradeIntent(
        symbol="BTCUSDT",
        side="BUY",
        proposed_notional=100.0,
        proposed_quantity=0.01,
        signal_quality=0.85,
        timestamp=datetime.now(timezone.utc).isoformat()
    )


@pytest.fixture
def clean_portfolio():
    return PortfolioState(
        wallet_value=10000.0,
        current_total_exposure=0.0,
        open_positions_count=0,
        per_symbol_exposure={}
    )


@pytest.fixture
def clean_system():
    return SystemState(
        consecutive_losses=0,
        consecutive_errors=0,
        daily_drawdown_pct=0.0,
        weekly_drawdown_pct=0.0
    )


@pytest.fixture
def healthy_market():
    return MarketState(
        adapter_health=True,
        market_snapshot_available=True,
        normalized_symbol="BTCUSDT",
        price=60000.0,
        volatility_score=0.01,
        regime="range"
    )


class TestGuardrailEngine:

    def test_approve_valid_trade(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        
        assert decision.ok is True
        assert decision.allowed is True
        assert decision.status == "approved"
        assert ReasonCode.APPROVED.value in decision.reason_codes

    def test_block_not_whitelisted_symbol(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        base_intent.symbol = "DOGEUSDT"
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        
        assert decision.allowed is False
        assert ReasonCode.SYMBOL_NOT_ALLOWED.value in decision.reason_codes

    def test_block_adapter_unhealthy(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        healthy_market.adapter_health = False
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        
        assert decision.allowed is False
        assert ReasonCode.ADAPTER_UNHEALTHY.value in decision.reason_codes

    def test_block_total_exposure(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        # Attempt to buy pushing exposure beyond max (30% di 10.000 = 3000)
        clean_portfolio.current_total_exposure = 2950.0  # Ci manca pochissimo al cup
        base_intent.proposed_notional = 100.0 # 2950 + 100 = 3050 (30.5%)
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        
        assert decision.allowed is False
        assert ReasonCode.TOTAL_EXPOSURE_LIMIT.value in decision.reason_codes

    def test_block_single_exposure(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        # Max single limit = 10% di 10.000 = 1000
        base_intent.proposed_notional = 1500.0 
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        assert decision.allowed is False
        assert ReasonCode.SINGLE_POSITION_LIMIT.value in decision.reason_codes

    def test_block_open_trades_limit(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        clean_portfolio.open_positions_count = 3
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        assert decision.allowed is False
        assert ReasonCode.TOO_MANY_OPEN_TRADES.value in decision.reason_codes

    def test_block_low_signal_quality(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        base_intent.signal_quality = 0.50  # policy asks for 0.60
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        assert decision.allowed is False
        assert ReasonCode.LOW_SIGNAL_QUALITY.value in decision.reason_codes

    def test_block_high_volatility(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        base_intent.volatility_score = 0.10  # policy block at 0.05
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        assert decision.allowed is False
        assert ReasonCode.HIGH_VOLATILITY.value in decision.reason_codes

    def test_block_system_cooldown(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        # Set cooldown in the future
        clean_system.system_cooldown_until = datetime.now(timezone.utc).timestamp() + 3600
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        assert decision.allowed is False
        assert ReasonCode.SYSTEM_COOLDOWN_ACTIVE.value in decision.reason_codes

    def test_block_drawdown(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        clean_system.daily_drawdown_pct = 0.05  # allowed max is 0.03
        
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        assert decision.allowed is False
        assert ReasonCode.DAILY_DRAWDOWN_LIMIT.value in decision.reason_codes
        
    def test_json_serialization(self, default_policy, base_intent, clean_portfolio, clean_system, healthy_market):
        engine = GuardrailEngine(default_policy)
        decision = engine.evaluate_trade_intent(base_intent, clean_portfolio, clean_system, healthy_market)
        
        dec_obj = decision.to_dict()
        assert "ok" in dec_obj
        assert dec_obj["status"] == "approved"
        assert dec_obj["risk_snapshot"]["portfolio"]["wallet_value"] == 10000.0
