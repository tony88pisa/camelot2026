import sys
from unittest.mock import MagicMock, patch

# 1. MOCKING AGGRESSIVO DELLE DIPENDENZE PRIMA DI QUALSIASI IMPORT
mock_logger = MagicMock()
mock_logger.info = MagicMock()
mock_logger.warning = MagicMock()
mock_logger.error = MagicMock()

# Mock dei moduli esterni
sys.modules["binance"] = MagicMock()
sys.modules["binance.client"] = MagicMock()
sys.modules["binance.streams"] = MagicMock()
sys.modules["flask"] = MagicMock()
sys.modules["flask_cors"] = MagicMock()

# Mock del logger factory
sys.modules["ai_trader.logging"] = MagicMock()
sys.modules["ai_trader.logging.jsonl_logger"] = MagicMock()
import ai_trader.logging.jsonl_logger
ai_trader.logging.jsonl_logger.get_logger.return_value = mock_logger

import pytest
from main import ApexReactor

@pytest.fixture
def mock_adapter():
    adapter = MagicMock()
    adapter.api_key = "key_exists"
    adapter.api_secret = "secret_exists"
    adapter.health_check.return_value = {"ok": True, "status": "ok"}
    adapter.get_account_summary.return_value = {"free_quote_balance": 100.0, "total_balance": 100.0}
    adapter.get_ticker_price.return_value = {"price": 60000.0}
    adapter.get_symbol_rules.return_value = {"minNotional": 10.0, "stepSize": 0.01}
    return adapter

@pytest.fixture
def reactor_live(mock_adapter):
    with patch("ai_trader.config.settings.get_settings") as mock_get_settings:
        # Whitelist corretta per lo staging (solo BTCUSDT)
        mock_get_settings.return_value.WHITELIST_PAIRS = ["BTCUSDT"]
        with patch("main.BinanceAdapter", return_value=mock_adapter):
            with patch("main.BinanceStreamer", return_value=MagicMock()):
                r = ApexReactor(mode="live")
                from ai_trader.risk.risk_kernel import RiskKernel
                from ai_trader.risk.risk_state_tracker import RiskStateTracker
                r.risk_kernel = RiskKernel()
                r.risk_tracker = RiskStateTracker()
                return r

class TestLiveReadiness:

    def test_gate_ok_healthy_staging(self, reactor_live):
        """Un ambiente live sano e ristretto deve passare il gate."""
        res = reactor_live._verify_live_readiness()
        assert res["ok"] is True
        assert len(res["errors"]) == 0

    def test_gate_blocked_by_whitelist_size(self, reactor_live):
        """Deve bloccare se la whitelist contiene simboli non autorizzati."""
        reactor_live.settings.WHITELIST_PAIRS = ["BTCUSDT", "DOGEUSDT"]
        res = reactor_live._verify_live_readiness()
        assert res["ok"] is False
        assert any("WHITELIST_NOT_IN_ALLOWED_SET" in e for e in res["errors"])

    def test_gate_blocked_by_missing_credentials(self, reactor_live, mock_adapter):
        """Deve bloccare se mancano le API Keys."""
        mock_adapter.api_key = None
        res = reactor_live._verify_live_readiness()
        assert res["ok"] is False
        assert "CREDENTIALS_MISSING" in res["errors"]

    def test_gate_blocked_by_exchange_health(self, reactor_live, mock_adapter):
        """Deve bloccare se l'exchange non  in salute."""
        mock_adapter.health_check.return_value = {"ok": False, "status": "maintenance"}
        res = reactor_live._verify_live_readiness()
        assert res["ok"] is False
        assert "EXCHANGE_UNHEALTHY: maintenance" in res["errors"]

    def test_capital_guard_discipline_sync(self, reactor_live):
        """Verifica deterministica della disciplina del capitale (sincrona)."""
        # Caso 1: Saldo 100 USDT -> 50% = 50, ma cap = 25. Risultato: 25.
        budget_capped = reactor_live._apply_capital_discipline(100.0)
        assert budget_capped == 25.0
        
        # Caso 2: Saldo 20 USDT -> 50% = 10, cap = 25. Risultato: 10.
        budget_capped_low = reactor_live._apply_capital_discipline(20.0)
        assert budget_capped_low == 10.0
        
        # Caso 3: Non live -> nessun cap.
        reactor_live.mode = "dry_run"
        budget_dry = reactor_live._apply_capital_discipline(100.0)
        assert budget_dry == 100.0
