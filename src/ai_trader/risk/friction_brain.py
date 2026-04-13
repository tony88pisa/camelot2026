# src/ai_trader/risk/friction_brain.py
# 2026-04-13 - Phase 6: Friction Brain (Cost Estimator)

import math
from typing import Dict, Any
from ai_trader.risk.opportunity_models import FrictionReport

class FrictionBrain:
    """Estimatore deterministico dei costi di transazione e impatto di mercato."""
    
    def __init__(self, maker_fee: float = 0.001, taker_fee: float = 0.001):
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        # Safety buffer per coprire variazioni improvvise di spread o slippage
        self.safety_buffer_pct = 0.0005 # 0.05%

    def estimate_friction(self, symbol: str, order_book: Dict[str, Any], notional: float) -> FrictionReport:
        """
        Calcola i costi stimati basandosi sullo stato attuale dell'order book.
        """
        # 1. Spread Calculation
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        
        if not bids or not asks:
            return FrictionReport(symbol=symbol, is_tradable=False, reason="EMPTY_ORDER_BOOK")
            
        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid_price = (best_bid + best_ask) / 2
        spread_pct = (best_ask - best_bid) / mid_price
        
        # 2. Slippage Estimation (Minimal implementation based on first levels)
        # Se il notional supera la profondit del primo livello, aggiungiamo slippage stimato
        first_level_qty = float(asks[0][1]) if asks else 0
        first_level_value = first_level_qty * best_ask
        
        slippage_est = 0.0
        if notional > first_level_value:
            # Stima conservativa: 0.1% di slippage extra ogni 2x il volume del primo livello
            multiples = notional / first_level_value
            slippage_est = min(0.01, (multiples - 1) * 0.001) 

        # 3. Total Friction (Round-trip conservative)
        # Consideriamo Taker fee per l'ingresso in staging live per sicurezza
        total_friction = self.taker_fee + (spread_pct / 2) + slippage_est + self.safety_buffer_pct
        
        return FrictionReport(
            symbol=symbol,
            fee_pct=self.taker_fee,
            spread_pct=spread_pct,
            slippage_est_pct=slippage_est,
            total_friction_pct=total_friction,
            is_tradable=True
        )
