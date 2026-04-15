# src/ai_trader/analysis/sentiment_connector.py
# 2026-04-13 - v10.4 Sentiment Engine

import json
from datetime import datetime
from typing import Dict, Any, List

from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("sentiment_connector")

class SentimentConnector:
    """
    Modulo di aggregazione del sentiment di mercato.
    Analizza news esterne, SuperMemory e indici di paura/avidit.
    """
    
    def __init__(self, supermemory=None):
        self.memory = supermemory # EpisodeStore
        logger.info("SentimentConnector inizializzato per v10.4")

    def get_market_sentiment(self, symbol: str) -> Dict[str, Any]:
        """
        Calcola il sentiment score (0.0-1.0) per un simbolo.
        0.0 = Estrema Paura, 1.0 = Estrema Avidit.
        """
        try:
            # In un sistema reale, qui chiameremmo API esterne o faremmo web search.
            # Per v10.4 simuliamo l'aggregazione basata su dati recenti di Aprile 2026.
            
            # 1. Analisi SuperMemory per il simbolo specifico (RAG Alimentato dal Demone gemma2:2b)
            final_score = 0.5  # Neutral default
            label = "NEUTRAL"
            
            if self.memory:
                # Prende gli eventi di sentiment_scan emessi dal daemon negli ultimi 50 log
                episodes = self.memory.load_episodes(category="research", limit=50)
                # Strip quote currency per matching (BTCEUR -> BTC, PEPEEUR -> PEPE)
                base_symbol = symbol.replace("EUR", "").replace("USDT", "")
                # Filtra per quelli del demone sentiment
                sentiment_events = [e for e in episodes if e.get("kind") == "sentiment_scan" and e.get("payload", {}).get("symbol") == base_symbol]
                
                if sentiment_events:
                    # Prende il più recente
                    latest = sentiment_events[-1]
                    verdict = latest.get("payload", {}).get("sentiment", "NEUTRAL").upper()
                    
                    if verdict == "BULLISH":
                        final_score = 0.8
                        label = "GREED"
                    elif verdict == "BEARISH":
                        final_score = 0.2
                        label = "FEAR"
                    else:
                        final_score = 0.5
                        label = "NEUTRAL"
                    
            result = {
                "symbol": symbol,
                "sentiment_score": round(final_score, 2),
                "label": label,
                "timestamp": datetime.now().isoformat(),
                "factors": {
                    "memory_rag": label
                }
            }
            
            logger.info(f"Sentiment Rilevato per {symbol}", score=final_score, label=label, source="gemma2:2b_daemon")
            return result

        except Exception as e:
            logger.error(f"Errore calcolo sentiment per {symbol}: {e}")
            return {"sentiment_score": 0.5, "label": "NEUTRAL", "error": str(e)}

if __name__ == "__main__":
    # Test Rapido
    connector = SentimentConnector()
    test_res = connector.get_market_sentiment("PEPEEUR")
    print(json.dumps(test_res, indent=2))
