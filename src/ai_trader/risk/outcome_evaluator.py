# src/ai_trader/risk/outcome_evaluator.py
# 2026-04-14 - Phase 7: Outcome Evaluator (Post-Rejection Review)

import time
from typing import Optional
from ai_trader.risk.opportunity_models import StructuredRejectedTrade, CounterfactualOutcome


class OutcomeEvaluator:
    """Valutazione deterministica della correttezza di una decisione di rifiuto passata."""

    def __init__(self, review_window_seconds: int = 3600):
        self.review_window_seconds = review_window_seconds

    def evaluate_rejection(
        self,
        record: StructuredRejectedTrade,
        current_price: float,
        current_time: Optional[float] = None,
    ) -> CounterfactualOutcome:
        """Valuta se un rifiuto passato era corretto confrontando il prezzo attuale."""
        now = current_time or time.time()
        move_multiplier = 1 if record.side == "BUY" else -1
        price_delta_pct = ((current_price - record.entry_price) / record.entry_price) * move_multiplier
        hypo_net_return = price_delta_pct - record.friction_total_pct
        is_correct = hypo_net_return <= record.threshold_used

        return CounterfactualOutcome(
            symbol=record.symbol,
            occurred_at=record.timestamp,
            evaluated_at=now,
            entry_price=record.entry_price,
            exit_price_60m=current_price,
            hypothetical_move_pct=price_delta_pct,
            hypothetical_net_return_pct=hypo_net_return,
            is_correct_rejection=is_correct,
            rejection_mode=record.rejection_mode,
        )
