# src/ai_trader/risk/capital_allocator.py
# 2026-04-13 - Phase 6: Capital Allocator (Sizing & Limits)

from typing import Optional
from ai_trader.risk.opportunity_models import ArbiterDecision, AllocationDecision

class CapitalAllocator:
    """Allocatore deterministico del capitale basato sulla qualit dell'opportunit."""
    
    def __init__(self, reserve_pct: float = 0.2, max_single_allocation: float = 25.0):
        # Riserva di sicurezza intoccabile (es. 20% del saldo libero)
        self.reserve_pct = reserve_pct
        self.max_single_allocation = max_single_allocation

    def allocate(self, decision: ArbiterDecision, settled_balance: float) -> AllocationDecision:
        """
        Determina quanto capitale allocare a un'opportunit approvata.
        """
        if not decision.allowed or not decision.candidate:
            return AllocationDecision(
                symbol=decision.candidate.symbol if decision.candidate else "NONE",
                action="NO_TRADE",
                reason=decision.reason_codes[0] if decision.reason_codes else "NOT_ALLOWED"
            )

        symbol = decision.candidate.symbol
        
        # 1. Calcolo Riserva
        reserve_amount = settled_balance * self.reserve_pct
        usable_balance = max(0.0, settled_balance - reserve_amount)
        
        if usable_balance <= 0 or usable_balance < 10.0: # 10 USDT soglia minima Binance
            return AllocationDecision(
                symbol=symbol,
                action="NO_TRADE",
                reason="INSUFFICIENT_SOLVENCY_AFTER_RESERVE"
            )

        # 2. Capital Sizing (v12.0 Iron Core Discipline)
        # Sizing basato sulla forza del segnale e qualit
        base_allocation = min(usable_balance, self.max_single_allocation)
        
        # Moltiplicatore per qualit (ALPHA=100%, BETA=70%, GAMMA=40%)
        quality_mult = 1.0
        if decision.quality.value == "BETA":
            quality_mult = 0.7
        elif decision.quality.value == "GAMMA":
            quality_mult = 0.4
            
        final_allocation = base_allocation * quality_mult * decision.candidate.signal_strength
        
        # 3. Floor check
        if final_allocation < 10.0:
            return AllocationDecision(
                symbol=symbol,
                action="NO_TRADE",
                reason=f"ALLOCATION_TOO_SMALL: {final_allocation:.2f} < 10.0"
            )

        return AllocationDecision(
            symbol=symbol,
            action=decision.candidate.side,
            allocated_notional=final_allocation,
            reserve_preserved=reserve_amount,
            reason="ALLOCATION_APPROVED"
        )
