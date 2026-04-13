import sys
from unittest.mock import MagicMock, patch

# Mockage preventivo totale per evitare side-effects di import in main.py
sys.modules["binance"] = MagicMock()
sys.modules["binance.client"] = MagicMock()
sys.modules["binance.streams"] = MagicMock()
sys.modules["flask"] = MagicMock()
sys.modules["flask_cors"] = MagicMock()

import pytest
# Ora possiamo importare ApexReactor senza crash di import
from main import ApexReactor

@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    # Mock regole standard: stepSize 0.01, minQty 0.01, minNotional 10.0
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
    
    # Mock dei metodi di snapping reali per testare il flusso end-to-end
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
    # Mock di get_settings per evitare caricamento file yaml reale
    with patch("main.get_settings") as mock_settings:
        mock_settings.return_value.WHITELIST_PAIRS = ["BTCUSDT"]
        r = ApexReactor(mock_adapter)
        r.grid_engine = MagicMock()
        return r

class TestExecutionHardening:

    def test_pre_flight_buy_min_notional(self, reactor):
        """Un ordine BUY USDT deve superare il minNotional."""
        # rules: minNotional 10.0. Noi mandiamo 5.0 -> deve fallire.
        res = reactor._pre_flight_check_order("BTCUSDT", "BUY", 5.0)
        assert res["ok"] is False
        assert "Min Notional" in res["error"]

    def test_pre_flight_sell_notional_after_snap(self, reactor, mock_adapter):
        """Un ordine SELL deve essere sopra minNotional DOPO lo snapping."""
        # rules: step 0.01, minNotional 10.0. Price: 100.0.
        # Se qty  0.099 -> snap(0.01) -> 0.09 -> 0.09 * 100 = 9.0 (Sotto 10 -> FALLISCE)
        res = reactor._pre_flight_check_order("BTCUSDT", "SELL", 0.099)
        assert res["ok"] is False
        assert "Min Notional" in res["error"]
        # Verifica che il normalizzatore sia stato usato
        assert res["normalized_qty"] == 0.09

    @pytest.mark.asyncio
    async def test_execute_order_reconciliation_zero_fill(self, reactor, mock_adapter):
        """Se l'ordine  ok ma executed_qty  0, non registrare sulla griglia."""
        # Bypassiamo il preflight reale per questo test
        with patch.object(reactor, "_pre_flight_check_order", return_value={"ok": True, "normalized_qty": 50.0}):
            mock_adapter.place_market_order.return_value = {
                "ok": True, "executed_qty": 0.0, "avg_price": 0.0, "status": "EXPIRED"
            }
            
            action = {"symbol": "BTCUSDT", "action": "BUY", "usdt_amount": 50.0, "level_index": 0}
            await reactor._execute_apex_order(action)
            
            reactor.grid_engine.record_buy.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_order_success_reconciliation(self, reactor, mock_adapter):
        """Successo: ordine eseguito e registrato con i valori reali dell'exchange."""
        with patch.object(reactor, "_pre_flight_check_order", return_value={"ok": True, "normalized_qty": 100.0}):
            mock_adapter.place_market_order.return_value = {
                "ok": True, "executed_qty": 100.0, "avg_price": 10.5, "status": "FILLED"
            }
            
            action = {"symbol": "BTCUSDT", "action": "BUY", "usdt_amount": 100.0, "level_index": 5}
            await reactor._execute_apex_order(action)
            
            reactor.grid_engine.record_buy.assert_called_with("BTCUSDT", 5, 10.5, 100.0)
