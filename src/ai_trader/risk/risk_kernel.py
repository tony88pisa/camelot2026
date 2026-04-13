# src/ai_trader/risk/risk_kernel.py
# 2026-04-13 - Phase 2: Independent Risk Kernel
"""
Nucleo decisionale sovrano per la protezione del capitale.
Valuta intenti di trading contro policy e stato reale del sistema.
"""

import time
from typing import Any
from ai_trader.risk.policy_models import (
    RiskPolicy, TradeIntent, PortfolioState, 
    SystemState, GuardrailDecision, ReasonCode
)

class RiskKernel:
    """Motore di valutazione del rischio deterministico e indipendente."""
    
    def __init__(self, policy: RiskPolicy = None):
        self.policy = policy or RiskPolicy()

    def evaluate_intent(
        self, 
        intent: TradeIntent, 
        portfolio: PortfolioState, 
        system: SystemState
    ) -> GuardrailDecision:
        """
        Punto di ingresso unico per la valutazione del rischio.
        Tutti i check devono passare per ottenere APPROVED.
        """
        reasons = []
        
        # 1. Kill-Switch (Hard Block)
        if self.policy.kill_switch_enabled:
            reasons.append(ReasonCode.SYSTEM_COOLDOWN_ACTIVE.value + ":KILL_SWITCH")
            
        # 2. Cooldown Globale
        now = time.time()
        if system.system_cooldown_until and now < system.system_cooldown_until:
            reasons.append(ReasonCode.SYSTEM_COOLDOWN_ACTIVE.value)
            
        # 3. Drawdown Giornaliero
        if system.daily_drawdown_pct >= self.policy.max_daily_drawdown_pct:
            reasons.append(ReasonCode.DAILY_DRAWDOWN_LIMIT.value)

        # 4. Serie di Perdite (Consecutive Losses)
        if system.consecutive_losses >= self.policy.max_consecutive_losses:
            reasons.append(ReasonCode.TOO_MANY_CONSECUTIVE_LOSSES.value)
            
        # 5. Serie di Errori (Consecutive Errors)
        if system.consecutive_errors >= self.policy.max_consecutive_errors:
            reasons.append(ReasonCode.TOO_MANY_CONSECUTIVE_ERRORS.value)

        # 6. Open Positions Count
        if portfolio.open_positions_count >= self.policy.max_open_trades:
            reasons.append(ReasonCode.TOO_MANY_OPEN_TRADES.value)

        # 7. Esposizione Totale Portafoglio
        # Calcoliamo l'impatto del nuovo trade
        new_total_exposure = portfolio.current_total_exposure + intent.proposed_notional
        max_total_notional = portfolio.wallet_value * self.policy.max_total_exposure_pct
        if new_total_exposure > max_total_notional:
            reasons.append(ReasonCode.TOTAL_EXPOSURE_LIMIT.value)

        # 7. Esposizione per Simbolo
        current_sym_exposure = portfolio.per_symbol_exposure.get(intent.symbol, 0.0)
        new_sym_exposure = current_sym_exposure + intent.proposed_notional
        max_sym_notional = portfolio.wallet_value * self.policy.max_symbol_exposure_pct
        if new_sym_exposure > max_sym_notional:
            reasons.append(ReasonCode.SINGLE_POSITION_LIMIT.value)

        # 8. Cooldown Simbolo Specifico
        sym_cooldown = system.symbol_cooldowns.get(intent.symbol, 0.0)
        if now < sym_cooldown:
            reasons.append(ReasonCode.SYMBOL_COOLDOWN_ACTIVE.value)

        # 9. Whitelist Check (Safety Guard)
        if intent.symbol not in self.policy.whitelist_pairs:
            reasons.append(ReasonCode.SYMBOL_NOT_ALLOWED.value)

        # 10. Signal Quality
        if intent.signal_quality < self.policy.min_signal_quality:
            reasons.append(ReasonCode.LOW_SIGNAL_QUALITY.value)

        # Verdetto Finale
        allowed = len(reasons) == 0
        status = "approved" if allowed else "blocked"
        
        # Risk Snapshot per audit
        snapshot = {
            "daily_drawdown": f"{system.daily_drawdown_pct:.4f}",
            "consecutive_losses": system.consecutive_losses,
            "total_exposure_pct": f"{(new_total_exposure/portfolio.wallet_value if portfolio.wallet_value > 0 else 0):.4f}",
            "symbol_exposure_pct": f"{(new_sym_exposure/portfolio.wallet_value if portfolio.wallet_value > 0 else 0):.4f}"
        }

        return GuardrailDecision(
            ok=True,
            allowed=allowed,
            status=status,
            reason_codes=reasons if reasons else [ReasonCode.APPROVED.value],
            normalized_symbol=intent.symbol,
            approved_notional=intent.proposed_notional if allowed else 0.0,
            risk_snapshot=snapshot
        )
