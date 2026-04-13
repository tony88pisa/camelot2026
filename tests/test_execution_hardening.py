import sys
import asyncio
from unittest.mock import MagicMock, patch

# 1. MOCKING AGGRESSIVO DELLE DIPENDENZE PRIMA DI QUALSIASI IMPORT
mock_logger = MagicMock()
# Impediamo al logger di fallire nella serializzazione JSON
mock_logger.info = MagicMock()
mock_logger.warning = MagicMock()
mock_logger.error = MagicMock()

sys.modules["binance"] = MagicMock()
sys.modules["binance.client"] = MagicMock()
sys.modules["binance.streams"] = MagicMock()
sys.modules["flask"] = MagicMock()
sys.modules["flask_cors"] = MagicMock()
# Mock del logger factory stesso
sys.modules["ai_trader.logging.jsonl_logger"] = MagicMock()
import ai_trader.logging.jsonl_logger
ai_trader.logging.jsonl_logger.get_logger.return_value = mock_logger

import pytest
from main import ApexReactor

@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.get_symbol_rules.return_value = {
        "stepSize": 0.01,
        "minQty": 0.01,
        "maxQty": 1000.0,
        "tickSize": 0.01,
        "minNotional": 10.0
    }
    adapter.get_ticker_price.return_value = {"price": 100.0}
    adapter.health_check.return_value = {"ok": True, "status": "ok"}
    adapter.get_account_summary.return_value = {"free_quote_balance": 1000.0}
    
    import math
    def mock_snap_q(sym, q):
        step = 0.01
        precision = 2
        factor = 10**precision
        return math.floor(q * factor) / factor
    adapter.snap_quantity.side_effect = mock_snap_q
    
    return adapter

@pytest.fixture
def reactor(mock_adapter):
    with patch("ai_trader.config.settings.get_settings") as mock_get_settings:
        mock_get_settings.return_value.WHITELIST_PAIRS = ["BTCUSDT"]
        with patch("main.BinanceAdapter", return_value=mock_adapter):
            with patch("main.BinanceStreamer", return_value=MagicMock()):
                r = ApexReactor()
                r.grid_engine = MagicMock()
                return r

class TestExecutionHardening:

    def test_pre_flight_buy_min_notional(self, reactor):
        res = reactor._pre_flight_check_order("BTCUSDT", "BUY", 5.0)
        assert res["ok"] is False
        assert "Min Notional" in res["error"]

    def test_pre_flight_sell_notional_after_snap(self, reactor, mock_adapter):
        mock_adapter.snap_quantity.return_value = 0.09
        res = reactor._pre_flight_check_order("BTCUSDT", "SELL", 0.099)
        assert res["ok"] is False
        assert "Min Notional" in res["error"]
        assert res["normalized_qty"] == 0.09

    def test_execute_order_reconciliation_zero_fill(self, reactor, mock_adapter):
        with patch.object(reactor, "_pre_flight_check_order", return_value={"ok": True, "normalized_qty": 50.0}):
            mock_adapter.place_market_order.return_value = {
                "ok": True, "executed_qty": 0.0, "avg_price": 0.0, "status": "EXPIRED"
            }
            action = {"symbol": "BTCUSDT", "action": "BUY", "usdt_amount": 50.0, "level_index": 0}
            asyncio.run(reactor._execute_apex_order(action))
            reactor.grid_engine.record_buy.assert_not_called()

    def test_execute_order_success_reconciliation(self, reactor, mock_adapter):
        with patch.object(reactor, "_pre_flight_check_order", return_value={"ok": True, "normalized_qty": 100.0}):
            mock_adapter.place_market_order.return_value = {
                "ok": True, "executed_qty": 100.0, "avg_price": 10.5, "status": "FILLED"
            }
            action = {"symbol": "BTCUSDT", "action": "BUY", "usdt_amount": 100.0, "level_index": 5}
            asyncio.run(reactor._execute_apex_order(action))
            reactor.grid_engine.record_buy.assert_called_with("BTCUSDT", 5, 10.5, 100.0)
