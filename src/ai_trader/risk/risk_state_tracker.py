# src/ai_trader/risk/risk_state_tracker.py
# 2026-04-13 - Phase 3A: Risk State Tracker
"""
Gestore in-memory dello stato di rischio real-time.
Memorizza metriche di esposizione, pnl stimato e serie di errori/perdite.
"""

import time
from typing import Dict, Any
from ai_trader.risk.policy_models import PortfolioState, SystemState

class RiskStateTracker:
    """Tracking deterministico dello stato di rischio per il RiskKernel."""
    
    def __init__(self):
        # Session state
        self.session_start_time = time.time()
        self.session_start_balance = 0.0
        self.current_wallet_value = 0.0
        
        # Exposure
        self.current_total_exposure = 0.0
        self.per_symbol_exposure: Dict[str, float] = {}
        self.open_positions_count = 0
        
        # Performance/Health
        self.consecutive_losses = 0
        self.consecutive_errors = 0
        self.estimated_daily_drawdown_pct = 0.0
        self.estimated_weekly_drawdown_pct = 0.0
        self.session_pnl = 0.0
        
        # Cooldowns
        self.system_cooldown_until = None
        self.symbol_cooldowns: Dict[str, float] = {}
        
        # Audit
        self.last_risk_block_reason = None

    def initialize_from_summary(self, summary: dict):
        """Sincronizzazione iniziale dall'account summary reale."""
        self.session_start_balance = summary.get("total_balance", 0.0)
        self.current_wallet_value = self.session_start_balance
        self.current_total_exposure = summary.get("total_exposure", 0.0)
        # Exposure granulare non ancora mappata in summary, inizializziamo vuota
        self.per_symbol_exposure = {} 
        self.open_positions_count = 0 # Placeholder per integrazione posizioni reali

    def record_order_fill(self, symbol: str, side: str, notional: float, qty: float):
        """Aggiorna lo stato dopo un fill confermato."""
        if side == "BUY":
            self.current_total_exposure += notional
            self.per_symbol_exposure[symbol] = self.per_symbol_exposure.get(symbol, 0.0) + notional
            # Nota: reset errori dopo fill positivo? 
            # Per ora teniamo le streak separate dagli ordini tecnici
        else: # SELL
            # Stima della riduzione esposizione
            self.current_total_exposure = max(0.0, self.current_total_exposure - notional)
            self.per_symbol_exposure[symbol] = max(0.0, self.per_symbol_exposure.get(symbol, 0.0) - notional)
            
        self.consecutive_errors = 0 # Ogni fill resetta la streak di errori tecnici

    def record_order_failure(self, error_type: str = "technical"):
        """Registra un fallimento tecnico o di rete."""
        self.consecutive_errors += 1

    def record_loss(self, amount: float):
        """Registra una perdita realizzata (pnl negativo)."""
        if amount < 0:
            self.consecutive_losses += 1
            self.session_pnl += amount
            self._update_drawdown()

    def record_gain(self, amount: float):
        """Registra un guadagno (resetta streak perdite)."""
        if amount > 0:
            self.consecutive_losses = 0
            self.session_pnl += amount
            self._update_drawdown()

    def record_risk_block(self, reason: str):
        """Registra un intervento del RiskKernel."""
        self.last_risk_block_reason = reason

    def _update_drawdown(self):
        """Calcola il drawdown stimato rispetto al balance iniziale."""
        if self.session_start_balance <= 0:
            return
        
        current_equity = self.session_start_balance + self.session_pnl
        if current_equity < self.session_start_balance:
            drawdown = (self.session_start_balance - current_equity) / self.session_start_balance
            self.estimated_daily_drawdown_pct = drawdown

    def get_portfolio_state(self) -> PortfolioState:
        """Genera snapshot per il RiskKernel."""
        return PortfolioState(
            wallet_value=self.current_wallet_value,
            current_total_exposure=self.current_total_exposure,
            open_positions_count=self.open_positions_count,
            per_symbol_exposure=self.per_symbol_exposure.copy()
        )

    def get_system_state(self) -> SystemState:
        """Genera snapshot per il RiskKernel."""
        return SystemState(
            consecutive_losses=self.consecutive_losses,
            consecutive_errors=self.consecutive_errors,
            daily_drawdown_pct=self.estimated_daily_drawdown_pct,
            weekly_drawdown_pct=self.estimated_weekly_drawdown_pct,
            session_pnl=self.session_pnl,
            system_cooldown_until=self.system_cooldown_until,
            symbol_cooldowns=self.symbol_cooldowns.copy(),
            last_risk_block_reason=self.last_risk_block_reason
        )
