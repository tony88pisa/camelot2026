# src/ai_trader/risk/night_session.py
# 2026-04-14 - Overnight Live Hardening: Session Safety Wrapper
"""
NightSession enforces hard constraints for unattended overnight trading.
All limits are session-scoped and cannot be relaxed at runtime.
Learning is write-only — no self-modification during the session.
"""

import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("night_session")


@dataclass
class NightSessionConfig:
    """Immutable overnight session constraints. Safety-first defaults."""
    allowed_symbols: list[str] = field(default_factory=lambda: ["BTCUSDT", "ETHUSDT"])
    max_open_positions: int = 1
    max_session_trades: int = 10
    max_session_loss_usd: float = 3.0
    max_notional_per_trade: float = 10.0
    trade_cooldown_sec: int = 300          # 5 min between trades
    rejection_cluster_threshold: int = 3   # after 3 consecutive rejections
    rejection_cluster_cooldown_sec: int = 600  # 10 min pause
    min_signal_quality: float = 0.75
    stale_data_max_age_sec: int = 120      # reject if data older than 2 min
    session_duration_hours: float = 8.0
    no_averaging_down: bool = True
    no_martingale: bool = True


class NightSession:
    """
    Session-level safety wrapper for overnight live trading.
    Tracks trade counts, session PnL, cooldowns, and enforces hard stops.
    """

    def __init__(self, config: Optional[NightSessionConfig] = None, report_dir: Optional[Path] = None):
        self.config = config or NightSessionConfig()
        self.session_start = time.time()
        self.session_end = self.session_start + (self.config.session_duration_hours * 3600)

        # Session counters
        self.trades_executed = 0
        self.session_pnl = 0.0
        self.consecutive_rejections = 0
        self.last_trade_time = 0.0
        self.open_positions: dict[str, float] = {}  # symbol -> notional

        # Hard stop flag
        self._halted = False
        self._halt_reason = ""

        # Morning report data
        self.trade_log: list[dict] = []
        self.rejection_log: list[dict] = []
        self.halt_events: list[dict] = []

        # Report output directory
        self.report_dir = report_dir or Path("reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "NightSession initialized",
            max_trades=self.config.max_session_trades,
            max_loss=self.config.max_session_loss_usd,
            max_notional=self.config.max_notional_per_trade,
            symbols=self.config.allowed_symbols,
            duration_h=self.config.session_duration_hours,
        )

    @property
    def is_halted(self) -> bool:
        """Check if session has been halted for any reason."""
        if self._halted:
            return True
        # Auto-halt checks
        if time.time() >= self.session_end:
            self._halt("SESSION_DURATION_EXPIRED")
            return True
        return False

    @property
    def halt_reason(self) -> str:
        return self._halt_reason

    def _halt(self, reason: str):
        """Trigger hard session stop."""
        if not self._halted:
            self._halted = True
            self._halt_reason = reason
            self.halt_events.append({
                "reason": reason,
                "timestamp": time.time(),
                "trades_executed": self.trades_executed,
                "session_pnl": self.session_pnl,
            })
            logger.warning(f"NIGHT SESSION HALTED: {reason}", pnl=self.session_pnl, trades=self.trades_executed)

    def check_trade_allowed(self, symbol: str, notional: float, signal_quality: float) -> tuple[bool, str]:
        """
        Pre-trade gate. Returns (allowed, reason).
        Must be called before every trade attempt.
        """
        # 1. Session halted
        if self.is_halted:
            return False, f"SESSION_HALTED:{self._halt_reason}"

        # 2. Symbol allowed
        if symbol not in self.config.allowed_symbols:
            return False, f"SYMBOL_NOT_IN_NIGHT_WHITELIST:{symbol}"

        # 3. Trade count cap
        if self.trades_executed >= self.config.max_session_trades:
            self._halt("MAX_SESSION_TRADES_REACHED")
            return False, "MAX_SESSION_TRADES_REACHED"

        # 4. Session loss cap
        if self.session_pnl <= -self.config.max_session_loss_usd:
            self._halt("MAX_SESSION_LOSS_REACHED")
            return False, f"MAX_SESSION_LOSS_REACHED:pnl={self.session_pnl:.2f}"

        # 5. Max open positions
        if len(self.open_positions) >= self.config.max_open_positions:
            return False, f"MAX_OPEN_POSITIONS:{len(self.open_positions)}"

        # 6. No averaging down
        if self.config.no_averaging_down and symbol in self.open_positions:
            return False, f"NO_AVERAGING_DOWN:{symbol}"

        # 7. Trade cooldown
        elapsed = time.time() - self.last_trade_time
        if self.last_trade_time > 0 and elapsed < self.config.trade_cooldown_sec:
            remaining = self.config.trade_cooldown_sec - elapsed
            return False, f"TRADE_COOLDOWN:{remaining:.0f}s_remaining"

        # 8. Rejection cluster cooldown
        if self.consecutive_rejections >= self.config.rejection_cluster_threshold:
            return False, f"REJECTION_CLUSTER_COOLDOWN:consecutive={self.consecutive_rejections}"

        # 9. Notional cap
        if notional > self.config.max_notional_per_trade:
            return False, f"NOTIONAL_EXCEEDS_CAP:{notional:.2f}>{self.config.max_notional_per_trade:.2f}"

        # 10. Signal quality
        if signal_quality < self.config.min_signal_quality:
            return False, f"SIGNAL_BELOW_NIGHT_THRESHOLD:{signal_quality:.2f}<{self.config.min_signal_quality:.2f}"

        return True, "APPROVED"

    def record_trade_executed(self, symbol: str, side: str, notional: float):
        """Record a trade that was actually executed."""
        self.trades_executed += 1
        self.last_trade_time = time.time()
        self.consecutive_rejections = 0  # reset on successful trade

        if side == "BUY":
            self.open_positions[symbol] = self.open_positions.get(symbol, 0.0) + notional

        self.trade_log.append({
            "timestamp": time.time(),
            "symbol": symbol,
            "side": side,
            "notional": notional,
            "trade_number": self.trades_executed,
            "session_pnl_at_time": self.session_pnl,
        })
        logger.info(
            f"NightSession: Trade #{self.trades_executed} recorded",
            symbol=symbol, side=side, notional=f"{notional:.2f}",
        )

    def record_trade_closed(self, symbol: str, realized_pnl: float):
        """Record a closed position and its realized PnL."""
        self.session_pnl += realized_pnl
        self.open_positions.pop(symbol, None)

        self.trade_log.append({
            "timestamp": time.time(),
            "symbol": symbol,
            "side": "CLOSE",
            "realized_pnl": realized_pnl,
            "session_pnl_after": self.session_pnl,
        })

        # Check session loss cap after close
        if self.session_pnl <= -self.config.max_session_loss_usd:
            self._halt("MAX_SESSION_LOSS_REACHED")

        logger.info(
            f"NightSession: Position closed",
            symbol=symbol, pnl=f"{realized_pnl:.4f}", session_pnl=f"{self.session_pnl:.4f}",
        )

    def record_rejection(self, symbol: str, reason: str):
        """Record a trade rejection for cluster tracking."""
        self.consecutive_rejections += 1
        self.rejection_log.append({
            "timestamp": time.time(),
            "symbol": symbol,
            "reason": reason,
            "consecutive_count": self.consecutive_rejections,
        })

    def reset_rejection_cluster(self):
        """Reset rejection counter (e.g., after cluster cooldown expires)."""
        self.consecutive_rejections = 0

    def generate_morning_report(self) -> dict:
        """Generate structured morning report for human review."""
        elapsed = time.time() - self.session_start
        report = {
            "session_id": f"night_{int(self.session_start)}",
            "started_at": self.session_start,
            "elapsed_hours": elapsed / 3600,
            "halted": self._halted,
            "halt_reason": self._halt_reason,
            "trades_executed": self.trades_executed,
            "session_pnl": self.session_pnl,
            "open_positions_at_end": dict(self.open_positions),
            "total_rejections": len(self.rejection_log),
            "halt_events": self.halt_events,
            "trade_log": self.trade_log,
            "rejection_log_summary": self.rejection_log[-10:] if self.rejection_log else [],
            "config_used": {
                "max_session_trades": self.config.max_session_trades,
                "max_session_loss_usd": self.config.max_session_loss_usd,
                "max_notional_per_trade": self.config.max_notional_per_trade,
                "allowed_symbols": self.config.allowed_symbols,
                "trade_cooldown_sec": self.config.trade_cooldown_sec,
            },
        }

        # Write to file
        report_path = self.report_dir / f"night_report_{int(self.session_start)}.json"
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, default=str)
            logger.info(f"Morning report written to {report_path}")
        except Exception as e:
            logger.error(f"Failed to write morning report: {e}")

        return report
