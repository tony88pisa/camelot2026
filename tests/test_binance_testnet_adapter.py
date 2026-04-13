# tests/test_binance_testnet_adapter.py
# 2026-04-03 01:05 - Test suite per Binance Testnet Adapter (Iron Core v12.0)
import pytest
from unittest.mock import MagicMock
from ai_trader.exchange.binance_testnet_adapter import BinanceTestnetAdapter


@pytest.fixture
def adapter_no_keys():
    """Restituisce un adapter inizializzato isolatamente senza chiavi (stringhe vuote per forzare l'assenza)."""
    return BinanceTestnetAdapter(
        base_url="https://mock.binance.vision",
        api_key="",
        api_secret=""
    )


@pytest.fixture
def adapter_with_keys():
    """Adapter con chiavi fake per bypassare blocchi."""
    return BinanceTestnetAdapter(
        base_url="https://mock.binance.vision",
        api_key="fakeApiKey123",
        api_secret="fakeApiSecret456"
    )


class TestBinanceTestnetAdapter:

    def test_init_no_crash_without_keys(self, adapter_no_keys):
        """L'inizializzazione senza chiavi non deve throware eccezioni."""
        assert adapter_no_keys._has_credentials() is False

    def test_normalize_symbol(self, adapter_no_keys):
        """Deve flat-pare i pair."""
        assert adapter_no_keys._normalize_symbol("BTC/USDT") == "BTCUSDT"
        assert adapter_no_keys._normalize_symbol("btc-usdt") == "BTCUSDT"

    def test_get_server_time_success(self, adapter_no_keys, monkeypatch):
        """Simula endpoint HTTP /api/v3/time pubblico."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"serverTime": 1700000000000}
        
        monkeypatch.setattr(adapter_no_keys.session, "get", lambda *args, **kwargs: mock_resp)
        
        res = adapter_no_keys.get_server_time()
        assert res["ok"] is True
        assert res["server_time"] == 1700000000000
        assert "server_time_iso" in res

    def test_get_ticker_price_success(self, adapter_no_keys, monkeypatch):
        """Simula fetch raw di un symbol."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"symbol": "BTCUSDT", "price": "1234.56"}
        
        monkeypatch.setattr(adapter_no_keys.session, "get", lambda *args, **kwargs: mock_resp)
        
        res = adapter_no_keys.get_ticker_price("btc/usdt")
        assert res["ok"] is True
        assert res["symbol"] == "BTCUSDT"
        assert res["price"] == 1234.56

    def test_get_account_snapshot_missing_keys(self, adapter_no_keys):
        """Endpoint privato deve bloccarsi a monte se mancano le creds."""
        res = adapter_no_keys.get_account_snapshot()
        assert res["ok"] is False
        assert res["status"] == "auth_missing"

    def test_get_account_snapshot_auth_failed(self, adapter_with_keys, monkeypatch):
        """Simula risposta Binance per chiavi invalide."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.json.return_value = {"code": -2015, "msg": "Invalid API-key, IP, or permissions for action."}
        
        monkeypatch.setattr(adapter_with_keys.session, "get", lambda *args, **kwargs: mock_resp)
        
        res = adapter_with_keys.get_account_snapshot()
        assert res["ok"] is False
        assert res["status"] == "auth_failed"

    def test_health_check_public_ok_private_missing(self, adapter_no_keys, monkeypatch):
        """Verifica lo stato parziale: public network alive ma auth keys mancanti."""
        monkeypatch.setattr(adapter_no_keys, "get_server_time", lambda: {"ok": True, "error": None})
        
        res = adapter_no_keys.health_check()
        assert res["ok"] is True
        assert res["api_keys_configured"] is False
        assert res["status"] == "partial"
