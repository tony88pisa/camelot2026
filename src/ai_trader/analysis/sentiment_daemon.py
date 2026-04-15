import sys
import os
import time
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
from datetime import datetime

# Path setup per eseguire questo file in standalone o integrato
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from ai_trader.core.ollama_client import OllamaClient
from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("sentiment_daemon")

class SentimentDaemon:
    """Demone RAG in background. Usa gemma2:2b per salvare sentiment in SuperMemory."""
    
    def __init__(self):
        self.store = EpisodeStore(os.path.join(project_root, "memdir/episodes"))
        # Usa il modello super leggero gemma2:2b 1.6GB
        self.client = OllamaClient(model="gemma2:2b", timeout=30)
        self.target_symbols = ["PEPE", "BTC", "ETH", "SOL", "BNB", "DOGE", "XRP", "ADA", "LINK", "AVAX"]
        
        # CAVEMAN PROMPT v14.0 — few token do trick
        self.system_prompt = (
            "Crypto sentiment classifier. "
            "Output EXACTLY 1 word: BULLISH or BEARISH or NEUTRAL. "
            "No other text."
        )

    def fetch_news_headlines(self, symbol: str, max_items: int = 4) -> str:
        """Scrape nativo del Web tramite DuckDuckGo, fallback su Google News RSS."""
        headlines = []
        
        # 1. Tentativo Ricerca Nativa Web (DuckDuckGo)
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = ddgs.news(f"{symbol} crypto", max_results=max_items)
                if results:
                    for r in results:
                        title = r.get("title", "")
                        source = r.get("source", "Web")
                        headlines.append(f"- [DDG: {source}] {title}")
        except Exception as e:
            logger.debug(f"DuckDuckGo API Issue (Rate limit/Block), fallback to RSS per {symbol}: {e}")

        # 2. Se DDG fallisce o è vuoto, usa il fallback Google RSS
        if not headlines:
            query = urllib.parse.quote(f"{symbol} crypto")
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    xml_data = response.read()
                
                root = ET.fromstring(xml_data)
                items = root.findall('.//item')
                
                for item in items[:max_items]:
                    title = item.findtext('title')
                    clean_title = title.split(" - ")[0] if " - " in title else title
                    headlines.append(f"- [RSS] {clean_title}")
                    
            except Exception as e:
                logger.error("RSS Fetch Error", symbol=symbol, error=str(e))
                
        return "\n".join(headlines)

    def evaluate_sentiment(self, symbol: str, headlines: str) -> str:
        """Invoca gemma2:2b limitando drasticamente i token in generazione per massima velocit."""
        user_prompt = f"Coin: {symbol}\n\nHeadlines:\n{headlines}\n\nSentiment:"
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        res = self.client.chat(messages, max_tokens=5, temperature=0.0)
        if res.get("ok"):
            return res["message"]["content"].strip()
        else:
            logger.error("Ollama Inference Error", symbol=symbol, error=res.get("error"))
            return "NEUTRAL"

    def run_cycle(self):
        """Esegue uno scan per tutti i simboli e salva in memoria."""
        logger.info("Avvio ciclo Sentiment RAG...")
        start_time = time.time()
        
        for sym in self.target_symbols:
            logger.info("Ricerca Web in corso...", symbol=sym)
            headlines = self.fetch_news_headlines(sym)
            
            if not headlines:
                continue
                
            sentiment_verdict = self.evaluate_sentiment(sym, headlines)
            
            # Salva il risultato in SuperMemory
            payload = {
                "symbol": sym,
                "sentiment": sentiment_verdict,
                "headlines_used": headlines.split("\n")
            }
            
            self.store.append_episode(
                category="research",
                kind="sentiment_scan",
                source="gemma2:2b",
                tags=[sym, sentiment_verdict.lower()],
                payload=payload
            )
            logger.info("Sentiment Memoria Salvata", symbol=sym, verdict=sentiment_verdict)
            
            # Pausa di raffreddamento tra le richieste API
            time.sleep(2)
            
        elapsed = time.time() - start_time
        logger.info(f"Ciclo completato. Tempo impiegato: {elapsed:.2f}s")
        
        # Rigenera l'indice markdown visivo di SuperMemory 
        try:
            from ai_trader.memory.memory_index import MemoryIndex
            MemoryIndex().update_memory_index()
            logger.info("SuperMemory Index (MEMORY.md) aggiornato con le news di Gemma2:2b")
        except Exception as e:
            logger.error("Errore aggiornamento MemoryIndex", error=str(e))

def run_loop(interval_seconds=3600):
    daemon = SentimentDaemon()
    while True:
        try:
            daemon.run_cycle()
        except Exception as e:
            logger.error("Errore fatale ciclo daemon", error=str(e))
        time.sleep(interval_seconds)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        SentimentDaemon().run_cycle()
    else:
        run_loop(interval_seconds=3600)  # default 1 hour
