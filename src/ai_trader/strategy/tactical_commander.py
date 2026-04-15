# src/ai_trader/strategy/tactical_commander.py
import json
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.core.ollama_client import OllamaClient

logger = get_logger("tactical_commander")

class TacticalCommander:
    """
    Cervello Tattico Ibrido (Hybrid MoE)
    Prende i dati dai sensori (Sentiment, Whale, Regime, Tech) e costringe
    gemma2:2b a emettere un Tactical Command secco usando il Caveman Prompt.
    """
    def __init__(self):
        self.ollama = OllamaClient(model="gemma2:2b", timeout=15)
        
        # CAVEMAN PROMPT v14.0 — few token do trick. Zero fluff.
        self.system_prompt = (
            "You are an AI Trading Commander. "
            "Analyze data. "
            "Output EXACTLY 1 word from: AGGRESSIVE_BUY, CAUTIOUS_BUY, HOLD, TAKE_PROFIT. "
            "No explanation."
        )

    def evaluate_tactical_state(self, symbol: str, sentiment: str, whale: dict, regime: str, tech: dict) -> str:
        """
        Interroga l'AI con contesto ridotto. Restituisce comando.
        """
        # Estrai info chiave minime
        whale_pressure = whale.get("pressure", "neutral")
        whale_walls = whale.get("walls_ratio", "N/A")
        rsi = tech.get("rsi", 50)
        trend = tech.get("trend_score", 0.0)

        # Costruisci input "Caveman" style
        user_prompt = f"""DATA FOR {symbol}:
SENTIMENT: {sentiment}
WHALE: {whale_pressure} (Walls: {whale_walls})
REGIME: {regime}
RSI: {rsi:.1f}
TREND: {trend:.2f}

COMMAND:"""
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        logger.info(f"TacticalCommander analyzing {symbol}...")
        res = self.ollama.chat(messages, max_tokens=6, temperature=0.0)
        
        if res.get("ok"):
            cmd = res["message"].get("content", "").strip().upper()
            
            # Pulizia e validazione del comando AI forzando l'adesione al set
            valid_commands = ["AGGRESSIVE_BUY", "CAUTIOUS_BUY", "HOLD", "TAKE_PROFIT"]
            for vcmd in valid_commands:
                if vcmd in cmd:
                    logger.info(f"Comando Tattico {symbol}: {vcmd} (Raw: {cmd})")
                    return vcmd
                    
            logger.warning(f"TacticalCommander hallucination: {cmd}. Holding.")
            return "HOLD"
        else:
            logger.error("TacticalCommander Inference Failed. Default to HOLD.")
            return "HOLD"
