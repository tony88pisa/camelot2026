# src/ai_trader/agents/whale_watch_agent.py
# 2026-04-13 - Apex Predator v11.0: Market Microstructure Analyst
"""
WhaleWatchAgent  Analizza lo squilibrio del libro ordini (OBI) e rileva muri di liquidit.
Identifica le manovre delle balene (Spoofing, Layering) in tempo reale.
"""

import math
from typing import Dict, Any, List, Optional
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("whale_watch")

class WhaleWatchAgent:
    """
    Agente specializzato nel monitoraggio della liquidit L2.
    Traduce i dati grezzi dell'Order Book in segnali di pressione (OBI).
    """

    def __init__(self, wall_multiplier: float = 3.0):
        self.wall_multiplier = wall_multiplier
        logger.info("WhaleWatchAgent: Inizializzato")

    def analyze_order_book(self, order_book: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analizza un libro ordini e restituisce metriche di pressione e muri.
        
        Args:
            order_book: {"bids": [[price, qty], ...], "asks": [...]}
            
        Returns:
            Dict con obi_score, detection_walls e recommendation.
        """
        if not order_book or not order_book.get("bids") or not order_book.get("asks"):
            return {"obi_score": 0.0, "walls": [], "status": "unknown"}

        bids = order_book["bids"]
        asks = order_book["asks"]

        # 1. Calcolo OBI (Order Book Imbalance) sui primi 10 livelli
        # Obiettivi 2026: Ponderazione sulla distanza dal prezzo medio
        bid_vol = sum(float(q) for p, q in bids[:10])
        ask_vol = sum(float(q) for p, q in asks[:10])
        
        obi = (bid_vol - ask_vol) / (bid_vol + ask_vol) if (bid_vol + ask_vol) > 0 else 0.0

        # 2. Wall Detection (Muri di balene)
        # Calcoliamo il volume medio dei primi 20 livelli come baseline
        avg_bid_vol = sum(float(q) for p, q in bids) / len(bids) if bids else 1.0
        avg_ask_vol = sum(float(q) for p, q in asks) / len(asks) if asks else 1.0

        walls = []
        
        # Cerca muri nei Bids (Supporto potenziale Balene)
        for p, q in bids:
            q_float = float(q)
            if q_float > avg_bid_vol * self.wall_multiplier:
                walls.append({"side": "BUY_WALL", "price": float(p), "qty": q_float, "strength": round(q_float / avg_bid_vol, 1)})
        
        # Cerca muri negli Asks (Resistenza potenziale Balene)
        for p, q in asks:
            q_float = float(q)
            if q_float > avg_ask_vol * self.wall_multiplier:
                walls.append({"side": "SELL_WALL", "price": float(p), "qty": q_float, "strength": round(q_float / avg_ask_vol, 1)})

        # 3. Interpretazione Strategica Apex Predator
        status = "neutral"
        if obi > 0.4: status = "heavy_buy_pressure"
        elif obi < -0.4: status = "heavy_sell_pressure"
        
        # Rilevamento "Guerra di Muri"
        buy_walls_count = len([w for w in walls if w["side"] == "BUY_WALL"])
        sell_walls_count = len([w for w in walls if w["side"] == "SELL_WALL"])

        return {
            "symbol": order_book.get("symbol"),
            "obi_score": round(obi, 3),
            "pressure": status,
            "walls": walls,
            "walls_ratio": f"B:{buy_walls_count} vs S:{sell_walls_count}",
            "is_manipulated": buy_walls_count > 3 or sell_walls_count > 3 # Sospetto spoofing
        }

    def get_predator_signal(self, o_book: Dict[str, Any]) -> str:
        """Restituisce raccomandazione basata puramente sui flussi L2."""
        analysis = self.analyze_order_book(o_book)
        obi = analysis["obi_score"]
        
        if obi > 0.6: return "STRONG_ACCUMULATION"
        if obi < -0.6: return "STRONG_DISTRIBUTION"
        
        # Check muri dominanti
        walls = analysis["walls"]
        big_buy_walls = [w for w in walls if w["side"] == "BUY_WALL" and w["strength"] > 5.0]
        big_sell_walls = [w for w in walls if w["side"] == "SELL_WALL" and w["strength"] > 5.0]
        
        if big_buy_walls and not big_sell_walls: return "WHALE_SUPPORT_DETECTED"
        if big_sell_walls and not big_buy_walls: return "WHALE_RESISTANCE_DETECTED"
        
        return "STABLE_FLOW"
