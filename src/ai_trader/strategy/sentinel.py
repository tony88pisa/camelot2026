# src/ai_trader/strategy/sentinel.py
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.config.settings import get_settings

logger = get_logger("sentinel")

class Sentinel:
    """
    Agente di intelligence che raccoglie notizie e sentiment per gli asset in whitelist.
    Sincronizza le informazioni su SuperMemory per il RAG del BrainAgent.
    """

    def __init__(self, episode_store: EpisodeStore = None):
        self.episode_store = episode_store or EpisodeStore()
        self.settings = get_settings()
        # Feed RSS di esempio (CoinTelegraph  affidabile e veloce)
        self.feeds = {
            "GENERAL": "https://cointelegraph.com/rss",
            "CARDANO": "https://cointelegraph.com/rss/tag/cardano",
            "BITCOIN": "https://cointelegraph.com/rss/tag/bitcoin",
            "ETHEREUM": "https://cointelegraph.com/rss/tag/ethereum"
        }

    def fetch_news(self, asset_tag: str = "GENERAL") -> list:
        """Recupera le news da un feed RSS."""
        url = self.feeds.get(asset_tag.upper(), self.feeds["GENERAL"])
        logger.info(f"Sentinel: Recupero news per {asset_tag}...", url=url)
        
        try:
            response = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                logger.error(f"Sentinel: Errore HTTP {response.status_code}")
                return []

            root = ET.fromstring(response.content)
            news_items = []
            for item in root.findall(".//item")[:5]: # Prendiamo le ultime 5
                title = item.find("title").text
                link = item.find("link").text
                pub_date = item.find("pubDate").text
                
                news_items.append({
                    "title": title,
                    "link": link,
                    "date": pub_date,
                    "asset": asset_tag
                })
            
            return news_items
        except Exception as e:
            logger.error(f"Sentinel: Errore recupero news: {e}")
            return []

    def store_news_in_memory(self, news_list: list):
        """Salva le news in SuperMemory via EpisodeStore."""
        for news in news_list:
            # Salviamo come 'research' category per attivare il sync
            self.episode_store.append_episode(
                category="research",
                kind="market_news",
                payload=news,
                tags=[news["asset"], "news", "sentiment"],
                source="Sentinel_v8.5"
            )
            logger.info(f"Sentinel: News archiviata: {news['title'][:50]}...")

    def update_intelligence(self, whitelist: list):
        """Ciclo completo di aggiornamento news per la whitelist in BACKGROUND v10.29."""
        import threading
        
        def _async_update():
            try:
                logger.info(f"Sentinel: Inizio aggiornamento intelligence asincrono per {whitelist}")
                # 1. News Generali
                general_news = self.fetch_news("GENERAL")
                self.store_news_in_memory(general_news)
                
                # 2. News specifiche per asset
                for asset in whitelist:
                    asset_prefix = asset.replace("EUR", "").replace("USDT", "").upper()
                    if asset_prefix in self.feeds:
                        asset_news = self.fetch_news(asset_prefix)
                        self.store_news_in_memory(asset_news)
                logger.info("Sentinel: Intelligence aggiornata (Perfect Circle)")
            except Exception as e:
                logger.error(f"Sentinel: Errore in background update: {e}")

        # Lancio il thread per non bloccare il loop principale
        thread = threading.Thread(target=_async_update, daemon=True)
        thread.start()
