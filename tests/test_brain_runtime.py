# tests/test_brain_runtime.py
# 2026-04-03 01:50 - TDD State Machine Runtime Orchestrator
import pytest
import os
from unittest.mock import MagicMock
from datetime import datetime, timezone

from ai_trader.brain.brain_types import BrainPhase, BrainContext, BrainEvent
from ai_trader.brain.brain_runtime import BrainRuntime
from ai_trader.strategy.policy_models import StrategyDecision
from ai_trader.execution.order_models import ExecutionPreviewDecision


@pytest.fixture
def mock_context():
    # Mock moduli per simulazione completa fluida runtime
    s_engine = MagicMock()
    # Costruiamo decision BUY
    s_engine.evaluate_signal.return_value = StrategyDecision(
        ok=True, status="buy_candidate", action="BUY", normalized_symbol="BTCUSDT",
        signal_quality=0.9, trend_score=0.9, volatility_score=0.01, confidence=0.9,
        reason_codes=[], thesis="mock_thesis", intent_preview={"symbol": "BTCUSDT", "side": "BUY", "proposed_quantity": 0.0, "proposed_notional": 20.0}
    )
    
    e_engine = MagicMock()
    e_engine.build_execution_preview.return_value = ExecutionPreviewDecision(
        ok=True, status="approved_preview", guardrail_allowed=True,
        reason_codes=[], paper_order={"id": 123}, risk_decision={}, error=None
    )
    
    ex_adapter = MagicMock()
    ex_adapter.get_ticker_price.return_value = {"price": 50000.0}
    
    mem_store = MagicMock()

    class MockSettings:
        WHITELIST_PAIRS = ["BTCUSDT", "ETHUSDT"]
        
    return BrainContext(
        settings=MockSettings(),
        exchange_adapter=ex_adapter,
        strategy_engine=s_engine,
        guardrail_engine=None,
        execution_preview_engine=e_engine,
        memory_store=mem_store,
        logger=MagicMock(),
        event_logger=None, # will fallback to global sink for pure push
        clock=MagicMock(),
        now_fn=lambda: datetime.now(timezone.utc).isoformat()
    )


def test_runtime_complete_lifecycle(mock_context):
    from unittest.mock import patch
    
    # Mock dell'analisi tecnica per garantire il passaggio a PROPOSE
    with patch("ai_trader.analysis.market_analyzer.MarketAnalyzer") as mock_analyzer_cls:
        mock_analyzer = mock_analyzer_cls.return_value
        mock_res = MagicMock()
        mock_res.ok = True
        mock_res.trend_score = 0.9
        mock_res.volatility_score = 0.01
        mock_res.regime = "bull"
        mock_res.signal_quality = 0.9
        mock_res.recommendation = "BUY"
        mock_analyzer.analyze.return_value = mock_res

        runtime = BrainRuntime(mock_context)
        runtime.start_cycle("CYCLE_MOCK")
        
        assert runtime.state is not None
        assert runtime.state.phase == BrainPhase.IDLE
        assert runtime.state.current_symbol == "BTCUSDT"
        
        # Tick -> Observe
        runtime.step()
        assert runtime.state.phase == BrainPhase.OBSERVE
        
        # Observe -> Analyze
        runtime.step()
        assert runtime.state.phase == BrainPhase.ANALYZE
        assert runtime.state.buffer_memory.get("market_price") == 50000.0
        
        # Analyze -> Propose
        runtime.step()
        assert runtime.state.phase == BrainPhase.PROPOSE
        assert "strategy_decision" in runtime.state.buffer_memory
        
        # Propose -> Guardrail Checked
        runtime.step()
        assert runtime.state.phase == BrainPhase.GUARDRAIL_CHECK
        
        # Guardrail Check -> Exec Preview
        runtime.step()
        assert runtime.state.phase == BrainPhase.EXECUTION_PREVIEW
        
        # Exec -> Review
        runtime.step()
        assert runtime.state.phase == BrainPhase.REVIEW
        assert "execution_decision" in runtime.state.buffer_memory
        
        # Review -> Learn
        runtime.step()
        assert runtime.state.phase == BrainPhase.LEARN
        assert "review_summary" in runtime.state.buffer_memory
        
        # Learn -> Sleep
        runtime.step()
        assert runtime.state.phase == BrainPhase.SLEEP
        mock_context.memory_store.append_episode.assert_called_once()


def test_runtime_error_fallback(mock_context):
    mock_context.exchange_adapter.get_ticker_price.side_effect = Exception("API down")
    
    runtime = BrainRuntime(mock_context)
    runtime.start_cycle("C2")
    runtime.step() # to observe
    runtime.step() # observe throws -> triggers exception -> emits error phase directly internally
    
    assert runtime.state.phase == BrainPhase.ERROR
    assert "API down" in str(runtime.state.last_error)
