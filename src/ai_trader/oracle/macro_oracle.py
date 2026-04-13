# src/ai_trader/oracle/macro_oracle.py
import json
import requests
from datetime import datetime, timezone
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.core.ollama_client import OllamaClient

logger = get_logger("macro_oracle")

class MacroOracle:
    """
    Modulo di Intelligence Macroeconomica e Geopolitica.
    Analizza i mega-trend globali (USA, Cina, Europa, Conflitti) 
    per generare un profilo di rischio strategico.
    """
    def __init__(self):
        self.ollama = OllamaClient(model="gemma4:latest")
        self.risk_score = 5  # 1 (Pace/Stabilit) -> 10 (Guerra Totale/Crollo)
        self.current_context = "Analisi iniziale mercati globali aprile 2026."

    def fetch_world_news(self) -> str:
        """
        Simulazione di ingestione news globali (via web search o feed).
        In produzione 2026 userebbe feed Reuters/Bloomberg/DEX-specific news.
        """
        # Simulazione bollettino geopolitico Aprile 2026 recuperato dalla ricerca web pre-esecuzione
        bulletin = (
            "1. Medio Oriente: Cessate il fuoco fragile (8 aprile). Tensione USA-Iran ancora alta.\n"
            "2. Trade War USA-Cina: Nuove restrizioni sui semiconduttori, ritorsioni cinesi sulle terre rare.\n"
            "3. Europa: Tassi di interesse stabili dopo la crisi energetica invernale.\n"
            "4. Crypto: BTC visto come hedge primario contro sanzioni e instabilit monetaria."
        )
        return bulletin

    def evaluate_macro_risk(self) -> dict:
        """Gemma 4 processa il bollettino mondiale e assegna un punteggio e una direzione."""
        news = self.fetch_world_news()
        
        prompt = f"""
        Sei il GENERALE STRATEGICO della Quantum Oracle Station. 
        Analizza la situazione geopolitica del 12 Aprile 2026:
        
        BOLLETTINO INTERNAZIONALE:
        {news}
        
        OBIETTIVO:
        1. Assegna un 'Geopolitical Risk Score' (1-10).
        2. Identifica il 'Market Mode' (WAR_HEDGE, RECOVERY, DE_RISKING, GROWTH).
        3. Suggerisci la lista monete ottimale in 'suggested_whitelist' (es: ["BTCUSDT", "XRPUSDT"]).
        4. Scrivi una 'Sentenza del Generale' (massimo 2 righe) per la dashboard.
        
        Rispondi ESCLUSIVAMENTE in formato JSON:
        {{
            "risk_score": int,
            "market_mode": "string",
            "suggested_whitelist": ["list"],
            "general_sentence": "string"
        }}
        """
        
        logger.info("L'Agente Profeta sta analizzando la Geopolitica Mondiale...")
        ai_res = self.ollama.chat([{"role": "user", "content": prompt}])
        
        if ai_res.get("ok"):
            try:
                # Pulizia per estrarre solo il JSON se l'AI aggiunge testo extra
                content = ai_res["message"].get("content", "{}")
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "{" in content:
                    content = "{" + content.split("{", 1)[1].rsplit("}", 1)[0] + "}"
                
                decision = json.loads(content)
                self.risk_score = decision.get("risk_score", 5)
                self.current_context = decision.get("general_sentence", "")
                logger.info("Analisi Macro completata", score=self.risk_score, mode=decision.get("market_mode"))
                return decision
            except Exception as e:
                logger.error("Errore parsing decisione macro", error=str(e))
                return {"risk_score": 5, "market_mode": "BALANCED"}
        
        return {"risk_score": 5, "market_mode": "BALANCED"}

    def get_vision(self) -> str:
        return self.current_context
