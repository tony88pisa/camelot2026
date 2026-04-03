# tests/test_execution_preview_engine.py
# 2026-04-03 01:35 - Suite Validazione Execution Proxy
import pytest
from datetime import datetime, timezone

from ai_trader.risk.policy_models import SystemState, MarketState, RiskPolicy
from ai_trader.risk.guardrail_engine import GuardrailEngine
from ai_trader.execution.order_models import ExecutionContext
from ai_trader.execution.execution_preview_engine import ExecutionPreviewEngine


@pytest.fixture
def mock_guardrail_whitelist_btc():
    policy = RiskPolicy(whitelist_pairs=["BTCUSDT"])
    return GuardrailEngine(policy)


@pytest.fixture
def safe_context():
    return ExecutionContext(
        wallet_value=10000.0,
        free_quote_balance=5000.0,
        open_positions_count=0,
        current_total_exposure=0.0,
        per_symbol_exposure={},
        system_state=SystemState(consecutive_losses=0, consecutive_errors=0, daily_drawdown_pct=0.0, weekly_drawdown_pct=0.0),
        market_state=MarketState(adapter_health=True, market_snapshot_available=True, normalized_symbol="BTCUSDT", price=50000.0, volatility_score=0.01, regime="normal")
    )


@pytest.fixture
def base_intent_preview():
    return {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "proposed_notional": 100.0,
        "proposed_quantity": 0.002,
        "signal_quality": 0.9,
        "regime": "normal",
        "volatility_score": 0.01,
        "source_agent": "test",
        "thesis": "Good trend",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


class TestExecutionPreviewEngine:

    def test_approve_valid_paper_order(self, mock_guardrail_whitelist_btc, safe_context, base_intent_preview):
        engine = ExecutionPreviewEngine(mock_guardrail_whitelist_btc)
        dec = engine.build_execution_preview(base_intent_preview, safe_context)
        
        assert dec.ok is True
        assert dec.status == "approved_preview"
        assert dec.guardrail_allowed is True
        assert "PREVIEW_APPROVED" in dec.reason_codes
        
        # Verify internal mapping checks
        assert dec.paper_order["symbol"] == "BTCUSDT"
        assert dec.paper_order["side"] == "BUY"
        assert dec.paper_order["order_type"] == "PAPER_MARKET"
        assert dec.paper_order["reference_price"] == 50000.0
        assert dec.paper_order["estimated_cost"] == 100.0

    def test_block_by_guardrail_limit(self, safe_context, base_intent_preview):
        # Override policy with aggressive cap trigger
        policy = RiskPolicy(whitelist_pairs=["BTCUSDT"], max_total_exposure_pct=0.0) 
        engine = ExecutionPreviewEngine(GuardrailEngine(policy))
        
        dec = engine.build_execution_preview(base_intent_preview, safe_context)
        
        assert dec.ok is False
        assert dec.status == "blocked"
        assert dec.guardrail_allowed is False
        assert "PREVIEW_BLOCKED_BY_GUARDRAIL" in dec.reason_codes
        assert "TOTAL_EXPOSURE_LIMIT" in dec.reason_codes # Guardrail code leak included!

    def test_insufficient_wallet_rejection(self, mock_guardrail_whitelist_btc, safe_context, base_intent_preview):
        # Limit the context freely available wallet drastically but leave overall value high enough for Risk Policy
        safe_context.free_quote_balance = 50.0  # Intent demands 100.0
        safe_context.wallet_value = 10000.0
        
        engine = ExecutionPreviewEngine(mock_guardrail_whitelist_btc)
        dec = engine.build_execution_preview(base_intent_preview, safe_context)
        
        assert dec.ok is False
        assert dec.status == "invalid"
        assert dec.guardrail_allowed is True  # Guardrail approved it, but layer found no liquid quote
        assert "INSUFFICIENT_WALLET" in dec.reason_codes

    def test_missing_price_rejection(self, mock_guardrail_whitelist_btc, safe_context, base_intent_preview):
        safe_context.market_state.price = 0.0
        engine = ExecutionPreviewEngine(mock_guardrail_whitelist_btc)
        dec = engine.build_execution_preview(base_intent_preview, safe_context)
        
        assert dec.ok is False
        assert "MISSING_REFERENCE_PRICE" in dec.reason_codes

    def test_missing_notional_calculates_from_qty(self, mock_guardrail_whitelist_btc, safe_context, base_intent_preview):
        base_intent_preview["proposed_notional"] = 0.0
        base_intent_preview["proposed_quantity"] = 0.01  # At price 50000, 0.01 = 500$
        
        engine = ExecutionPreviewEngine(mock_guardrail_whitelist_btc)
        dec = engine.build_execution_preview(base_intent_preview, safe_context)
        
        assert dec.ok is True
        assert dec.paper_order["proposed_notional"] == 500.0
        assert dec.paper_order["estimated_cost"] == 500.0

    def test_invalid_symbol_or_missing(self, mock_guardrail_whitelist_btc, safe_context, base_intent_preview):
        base_intent_preview["symbol"] = ""
        engine = ExecutionPreviewEngine(mock_guardrail_whitelist_btc)
        dec = engine.build_execution_preview(base_intent_preview, safe_context)
        
        assert dec.ok is False
        assert "INVALID_SYMBOL" in dec.reason_codes
        
    def test_buy_only_enforced(self, mock_guardrail_whitelist_btc, safe_context, base_intent_preview):
        base_intent_preview["side"] = "SELL" # Mock Short attempts
        engine = ExecutionPreviewEngine(mock_guardrail_whitelist_btc)
        dec = engine.build_execution_preview(base_intent_preview, safe_context)
        
        assert dec.ok is False
        assert "INVALID_SIDE" in dec.reason_codes

    def test_json_stability(self, mock_guardrail_whitelist_btc, safe_context, base_intent_preview):
        engine = ExecutionPreviewEngine(mock_guardrail_whitelist_btc)
        dec = engine.build_execution_preview(base_intent_preview, safe_context)
        js = dec.to_dict()
        assert js["ok"] is True
        assert js["status"] == "approved_preview"
        assert type(js["paper_order"]) is dict
        assert js["paper_order"]["order_type"] == "PAPER_MARKET"
