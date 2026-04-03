# tests/test_strategy_policy_engine.py
# 2026-04-03 01:25 - Suite validatrice Strategy Engine
import pytest
from datetime import datetime, timezone

from ai_trader.strategy.policy_models import StrategyPolicy, SignalInput
from ai_trader.strategy.strategy_policy_engine import StrategyPolicyEngine
from ai_trader.strategy.intent_preview import DEFAULT_PROPOSED_NOTIONAL


@pytest.fixture
def default_policy():
    return StrategyPolicy(
        allowed_symbols=["BTCUSDT", "ETHUSDT"],
        min_signal_quality=0.65,
        min_trend_score=0.50,
        max_volatility_score=0.05,
        require_memory_context=False
    )


@pytest.fixture
def valid_signal():
    return SignalInput(
        symbol="BTCUSDT",
        price=60000.0,
        timestamp=datetime.now(timezone.utc).isoformat(),
        trend_score=0.80,
        volatility_score=0.02,
        regime="bull",
        signal_quality=0.90,
        adapter_health=True,
        market_snapshot_available=True
    )


class TestStrategyPolicyEngine:

    def test_evaluate_valid_buy_candidacy(self, default_policy, valid_signal):
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)

        assert decision.ok is True
        assert decision.action == "BUY"
        assert decision.status == "buy_candidate"
        assert "BUY_CANDIDATE" in decision.reason_codes
        
        # Checking intent preview creation
        assert "symbol" in decision.intent_preview
        assert decision.intent_preview["side"] == "BUY"
        assert decision.intent_preview["proposed_notional"] == DEFAULT_PROPOSED_NOTIONAL
        assert decision.intent_preview["proposed_quantity"] == DEFAULT_PROPOSED_NOTIONAL / 60000.0

    def test_evaluate_hold_for_low_quality(self, default_policy, valid_signal):
        valid_signal.signal_quality = 0.50  # policy is 0.65
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)

        assert decision.action == "HOLD"
        assert decision.status == "hold"
        assert "LOW_SIGNAL_QUALITY" in decision.reason_codes
        assert hasattr(decision, "intent_preview")
        assert decision.intent_preview == {}  # Empty on hold

    def test_evaluate_skip_for_high_volatility(self, default_policy, valid_signal):
        valid_signal.volatility_score = 0.10  # policy cap 0.05
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)

        assert decision.ok is False
        assert decision.action == "SKIP"
        assert decision.status == "blocked"
        assert "HIGH_VOLATILITY" in decision.reason_codes
        assert decision.confidence == 0.0

    def test_evaluate_skip_for_blocked_regime(self, default_policy, valid_signal):
        valid_signal.regime = "forbidden"
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)

        assert decision.action == "SKIP"
        assert decision.status == "blocked"
        assert "REGIME_BLOCKED" in decision.reason_codes

    def test_evaluate_symbol_not_supported(self, default_policy, valid_signal):
        valid_signal.symbol = "DOGE_USDT"
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)

        assert decision.action == "SKIP"
        assert decision.status == "blocked"
        assert "SYMBOL_NOT_SUPPORTED" in decision.reason_codes

    def test_evaluate_adapter_unhealthy(self, default_policy, valid_signal):
        valid_signal.adapter_health = False
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)

        assert decision.action == "SKIP"
        assert "ADAPTER_UNAVAILABLE" in decision.reason_codes

    def test_evaluate_market_snapshot_missing(self, default_policy, valid_signal):
        valid_signal.market_snapshot_available = False
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)

        assert decision.action == "SKIP"
        assert "MARKET_SNAPSHOT_MISSING" in decision.reason_codes

    def test_evaluate_memory_context_missing_forced(self, default_policy, valid_signal):
        default_policy.require_memory_context = True # Forcing constraint
        valid_signal.memory_summary = ""
        
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)

        assert decision.action == "SKIP"
        assert "MEMORY_CONTEXT_MISSING" in decision.reason_codes

    def test_json_output_format(self, default_policy, valid_signal):
        engine = StrategyPolicyEngine(default_policy)
        decision = engine.evaluate_signal(valid_signal)
        
        out = decision.to_dict()
        assert "action" in out
        assert "thesis" in out
        assert out["ok"] is True
        assert type(out["intent_preview"]) == dict
