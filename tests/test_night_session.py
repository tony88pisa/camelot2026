# tests/test_night_session.py
# 2026-04-14 - Night Live Hardening: Safety Constraint Tests

import time
import pytest
from ai_trader.risk.night_session import NightSession, NightSessionConfig


@pytest.fixture
def session():
    """Create a NightSession with default safety constraints."""
    config = NightSessionConfig()
    return NightSession(config=config, report_dir=None)


@pytest.fixture
def tight_session():
    """Create a NightSession with very tight limits for edge-case testing."""
    config = NightSessionConfig(
        max_session_trades=2,
        max_session_loss_usd=1.0,
        max_open_positions=1,
        trade_cooldown_sec=0,  # disable cooldown for fast tests
        rejection_cluster_threshold=2,
        min_signal_quality=0.50,
    )
    return NightSession(config=config, report_dir=None)


class TestNightSessionSafety:
    """Tests for all 15 overnight safety constraints."""

    def test_symbol_whitelist(self, session):
        """Only BTCUSDT and ETHUSDT are allowed overnight."""
        ok, reason = session.check_trade_allowed("BTCUSDT", 10.0, 0.80)
        assert ok is True
        ok, reason = session.check_trade_allowed("DOGEUSDT", 10.0, 0.80)
        assert ok is False
        assert "SYMBOL_NOT_IN_NIGHT_WHITELIST" in reason

    def test_max_session_trades_halt(self, tight_session):
        """Bot halts after max_session_trades is reached."""
        tight_session.record_trade_executed("BTCUSDT", "BUY", 10.0)
        tight_session.record_trade_closed("BTCUSDT", 0.01)
        tight_session.record_trade_executed("ETHUSDT", "BUY", 10.0)
        tight_session.record_trade_closed("ETHUSDT", 0.01)
        ok, reason = tight_session.check_trade_allowed("BTCUSDT", 10.0, 0.80)
        assert ok is False
        assert tight_session.is_halted
        assert "MAX_SESSION_TRADES" in reason

    def test_session_loss_halt(self, tight_session):
        """Bot halts when session loss exceeds cap."""
        tight_session.record_trade_executed("BTCUSDT", "BUY", 10.0)
        tight_session.record_trade_closed("BTCUSDT", -1.5)  # -$1.5 > $1 cap
        assert tight_session.is_halted
        assert "MAX_SESSION_LOSS" in tight_session.halt_reason

    def test_max_open_positions(self, tight_session):
        """Only 1 open position allowed at a time."""
        tight_session.record_trade_executed("BTCUSDT", "BUY", 10.0)
        ok, reason = tight_session.check_trade_allowed("ETHUSDT", 10.0, 0.80)
        assert ok is False
        assert "MAX_OPEN_POSITIONS" in reason

    def test_no_averaging_down(self):
        """Cannot add to an existing position even when more positions are allowed."""
        config = NightSessionConfig(
            max_open_positions=3,  # allow multiple positions to isolate averaging check
            trade_cooldown_sec=0,
        )
        s = NightSession(config=config, report_dir=None)
        s.record_trade_executed("BTCUSDT", "BUY", 10.0)
        # Try to buy more BTCUSDT (averaging down)
        ok, reason = s.check_trade_allowed("BTCUSDT", 5.0, 0.80)
        assert ok is False
        assert "NO_AVERAGING_DOWN" in reason

    def test_notional_cap(self, session):
        """Per-trade notional cannot exceed cap."""
        ok, reason = session.check_trade_allowed("BTCUSDT", 50.0, 0.80)
        assert ok is False
        assert "NOTIONAL_EXCEEDS_CAP" in reason

    def test_signal_quality_threshold(self, session):
        """Overnight requires higher signal quality (0.75)."""
        ok, reason = session.check_trade_allowed("BTCUSDT", 10.0, 0.60)
        assert ok is False
        assert "SIGNAL_BELOW_NIGHT_THRESHOLD" in reason

    def test_rejection_cluster_cooldown(self, tight_session):
        """After N consecutive rejections, trading pauses."""
        tight_session.record_rejection("BTCUSDT", "LOW_EDGE")
        tight_session.record_rejection("BTCUSDT", "LOW_EDGE")
        ok, reason = tight_session.check_trade_allowed("BTCUSDT", 10.0, 0.80)
        assert ok is False
        assert "REJECTION_CLUSTER" in reason

    def test_trade_cooldown(self, session):
        """Cooldown enforced between trades."""
        session.record_trade_executed("BTCUSDT", "BUY", 10.0)
        session.record_trade_closed("BTCUSDT", 0.01)
        # Immediately try another trade
        ok, reason = session.check_trade_allowed("ETHUSDT", 10.0, 0.80)
        assert ok is False
        assert "TRADE_COOLDOWN" in reason

    def test_session_duration_halt(self):
        """Session halts after duration expires."""
        config = NightSessionConfig(session_duration_hours=0.0)  # expire immediately
        s = NightSession(config=config, report_dir=None)
        import time; time.sleep(0.01)
        assert s.is_halted
        assert "SESSION_DURATION_EXPIRED" in s.halt_reason

    def test_morning_report_generation(self, tight_session):
        """Morning report has all required fields."""
        tight_session.record_trade_executed("BTCUSDT", "BUY", 10.0)
        tight_session.record_trade_closed("BTCUSDT", 0.05)
        report = tight_session.generate_morning_report()
        assert "session_id" in report
        assert report["trades_executed"] == 1
        assert report["session_pnl"] == 0.05
        assert "config_used" in report
        assert "trade_log" in report

    def test_halted_session_blocks_all_trades(self, session):
        """Once halted, no trades can proceed."""
        session._halt("TEST_HALT")
        ok, reason = session.check_trade_allowed("BTCUSDT", 5.0, 0.99)
        assert ok is False
        assert "SESSION_HALTED" in reason

    def test_approved_trade_flow(self, session):
        """A valid trade passes all checks."""
        session.last_trade_time = 0  # no cooldown needed for first
        ok, reason = session.check_trade_allowed("BTCUSDT", 10.0, 0.80)
        assert ok is True
        assert reason == "APPROVED"
