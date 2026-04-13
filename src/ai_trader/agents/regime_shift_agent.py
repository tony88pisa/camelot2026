# src/ai_trader/agents/regime_shift_agent.py
# 2026-04-13 - Apex Predator v11.0: Market State Supervisor
"""
RegimeShiftAgent  Identifica lo stato fondamentale del mercato.
Decide il profilo di rischio e la strategia dominante (Aggressiva vs Difensiva).
"""

from dataclasses import dataclass
from typing import Dict, List, Any
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("regime_shift")

@dataclass
class MarketRegime:
    name: str               # "BULL" | "BEAR" | "CHOP" | "VOLATILE"
    risk_level: float       # 0.0 (nessun rischio) a 1.0 (massimo rischio)
    tp_multiplier: float    # Moltiplicatore per i target di profitto
    max_drawdown_limit: float # Limite di stop-loss dinamico per questo regime

class RegimeShiftAgent:
    """
    Supervisore AI che classifica le fasi di mercato.
    Agisce come un selettore di marce per il motore del bot.
    """

    def __init__(self):
        # Database dei regimi standard 2026
        self.regimes = {
            "BULL": MarketRegime("BULL", 0.8, 1.5, 5.0),
            "BEAR": MarketRegime("BEAR", 0.2, 0.5, 2.0),
            "CHOP": MarketRegime("CHOP", 0.5, 0.8, 3.0),
            "VOLATILE": MarketRegime("VOLATILE", 0.4, 2.0, 10.0)
        }
        self.current_regime = self.regimes["CHOP"]
        logger.info("RegimeShiftAgent: Inizializzato")

    def detect_regime(self, market_data: Dict[str, Any], whale_signal: str) -> MarketRegime:
        """
        Classifica il regime corrente combinando tecnica e microstruttura.
        """
        trend = market_data.get("trend_score", 0.0)
        volatility = market_data.get("volatility_score", 0.0)
        rsi = market_data.get("rsi", 50.0)

        # Regola 1: Volatility Overdrive (Panic o Euphoria)
        if volatility > 0.05: # Soglia alta per 2026
            self.current_regime = self.regimes["VOLATILE"]
        
        # Regola 2: Trend Bullish confermato
        elif trend > 0.3 and rsi < 70:
            self.current_regime = self.regimes["BULL"]
            
        # Regola 3: Trend Bearish o Whale Distribution
        elif trend < -0.3 or "DISTRIBUTION" in whale_signal:
            self.current_regime = self.regimes["BEAR"]
            
        # Default: Mercato incerto o laterale
        else:
            self.current_regime = self.regimes["CHOP"]

        logger.info(f" Cambio Regime Rilevato: {self.current_regime.name}", 
                    trend=trend, vol=volatility, whale=whale_signal)
        
        return self.current_regime

    def get_strategy_adjustments(self) -> Dict[str, Any]:
        """Restituisce i parametri di aggiustamento per gli altri moduli."""
        r = self.current_regime
        return {
            "risk_weight": r.risk_level,
            "tp_boost": r.tp_multiplier,
            "stop_limit": r.max_drawdown_limit,
            "grid_density": "tight" if r.name == "CHOP" else "wide"
        }
