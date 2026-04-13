# src/ai_trader/oracle/global_oracle.py
import requests
import json
from datetime import datetime, timezone
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.core.ollama_client import OllamaClient

logger = get_logger("global_oracle")

class GlobalOracle:
    """
    L'Oracolo Globale: Scansiona il mondo esterno per nutrire il cervello dell'AI.
    Utilizza API pubbliche per sentiment e market data.
    """
    def __init__(self):
        self.ollama = OllamaClient(model="gemma4:latest")
        self.last_bulletin = None
        self.last_update = None
        
    def fetch_sentiment(self) -> dict:
        """Recupera il sentiment globale da CryptoPanic (Public Feed)."""
        try:
            # Versione public (senza API key per ora, usa i feed pubblici se possibile)
            url = "https://cryptopanic.com/api/v1/posts/?public=true"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                return {"ok": True, "results": data.get("results", [])[:10]}
            return {"ok": False, "error": f"Status {res.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def fetch_global_market(self) -> dict:
        """Recupera i top asset e trend da CoinGecko."""
        try:
            url = "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=20&page=1"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                return {"ok": True, "data": res.json()}
            return {"ok": False, "error": f"Status {res.status_code}"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def generate_oracle_bulletin(self) -> str:
        """Gemma 4 analizza i dati globali e genera una direzione strategica."""
        sentiment = self.fetch_sentiment()
        market = self.fetch_global_market()
        
        prompt = f"""
        Sei l'ORACOLO QUANTISTICO 2026. Analizza i dati correnti:
        
        SENTIMENT NEWS: {json.dumps(sentiment.get('results', []), default=str)}
        GLOBAL MARKET TOP 20: {json.dumps(market.get('data', []), default=str)}
        
        OBIETTIVO:
        1. Qual  il 'Mood' del mercato oggi? (Extreme Fear, Fear, Neutral, Greed, Extreme Greed)
        2. Quali sono i 3 simboli pi promettenti su cui il bot dovrebbe concentrarsi?
        3. C' un pericolo imminente rilevato nelle news?
        
        Rispondi in formato sintetico per il consumo interno del sistema.
        """
        
        logger.info("Generazione Bollettino Oracolare via Gemma 4...")
        ai_res = self.ollama.chat([{"role": "user", "content": prompt}])
        
        if ai_res.get("ok"):
            self.last_bulletin = ai_res["message"].get("content", "Nessun dato.")
            self.last_update = datetime.now(timezone.utc).isoformat()
            logger.info("Bollettino Oracolare generato con successo.")
            return self.last_bulletin
        
        return "Errore nella generazione del bollettino."

    def get_status(self) -> dict:
        return {
            "last_update": self.last_update,
            "bulletin": self.last_bulletin
        }
