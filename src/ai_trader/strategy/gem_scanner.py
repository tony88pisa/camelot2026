# src/ai_trader/strategy/gem_scanner.py
# 2026-04-14 - Gem Scanner: Paper Trading Parallelo per Nuovi Listing
"""
Gem Scanner - Modulo ESTERNO di osservazione.

NON esegue trade reali. Monitora nuovi listing su Binance,
valuta il sentiment con gemma2:2b, e simula acquisti in un
portafoglio fantasma per confrontare i risultati col bot principale.
"""

import json
import time
import sys
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../.."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

from ai_trader.core.ollama_client import OllamaClient
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("gem_scanner")

GEM_STATE_FILE = Path("data/gems/gem_paper_portfolio.json")
GEM_WATCHLIST_FILE = Path("data/gems/gem_watchlist.json")


@dataclass
class PaperTrade:
    """Trade simulato (paper) per valutazione."""
    symbol: str
    entry_price: float
    entry_time: str
    quantity: float  # Simulato: budget / price
    budget_eur: float
    sentiment_at_entry: str
    current_price: float = 0.0
    unrealized_pnl_pct: float = 0.0
    status: str = "open"  # open, closed


class GemScanner:
    """
    Scanner per gemme crypto.
    
    Funzionamento:
    1. Cerca nuove monete su Google News con keywords specifiche
    2. Usa gemma2:2b per valutare il potenziale
    3. Se promettente, registra un "paper trade" simulato
    4. Tiene traccia del PnL virtuale rispetto al bot Grid/DCA reale
    """
    
    def __init__(self):
        self.client = OllamaClient(model="gemma2:2b", timeout=30)
        self.paper_trades: list[dict] = []
        self.watchlist: list[str] = []
        self.virtual_budget = 120.0  # Simula lo stesso budget dell'utente
        self.virtual_spent = 0.0
        self._load_state()

    def _load_state(self):
        """Carica stato paper portfolio."""
        GEM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if GEM_STATE_FILE.exists():
            try:
                with open(GEM_STATE_FILE, "r") as f:
                    data = json.load(f)
                self.paper_trades = data.get("trades", [])
                self.virtual_spent = data.get("virtual_spent", 0.0)
            except Exception:
                pass

    def _save_state(self):
        """Salva stato su disco."""
        GEM_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "trades": self.paper_trades,
            "virtual_spent": self.virtual_spent,
            "last_update": datetime.now(timezone.utc).isoformat()
        }
        with open(GEM_STATE_FILE, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def discover_trending_gems(self) -> list[dict]:
        """Cerca nuove monete trending su Google News."""
        keywords = [
            "new crypto listing Binance 2026",
            "crypto gem low cap moonshot",
            "Binance Alpha new token launch",
            "memecoin presale launch 100x"
        ]
        
        all_headlines = []
        for kw in keywords:
            query = urllib.parse.quote(kw)
            url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    xml_data = resp.read()
                root = ET.fromstring(xml_data)
                for item in root.findall('.//item')[:3]:
                    title = item.findtext('title', '')
                    clean = title.split(" - ")[0] if " - " in title else title
                    all_headlines.append({"title": clean, "keyword": kw})
            except Exception as e:
                logger.error(f"RSS gem scan error: {e}")
                continue
            time.sleep(1)  # Rate limiting
        
        return all_headlines

    def evaluate_gem_potential(self, headlines: list[dict]) -> list[dict]:
        """Usa gemma2:2b per valutare il potenziale delle gemme trovate."""
        if not headlines:
            return []

        headlines_text = "\n".join(f"- {h['title']}" for h in headlines)
        
        system_prompt = (
            "You are a crypto gem analyst. Read the headlines below about new crypto tokens. "
            "Extract any specific coin/token ticker symbols mentioned (e.g., $PEPE, $DOGE). "
            "For each ticker found, rate its potential as HIGH, MEDIUM, or LOW. "
            "Output format: TICKER:RATING (one per line). "
            "If no specific tickers are found, output NONE."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Headlines:\n{headlines_text}\n\nAnalysis:"}
        ]
        
        res = self.client.chat(messages, max_tokens=50, temperature=0.0)
        
        gems = []
        if res.get("ok"):
            content = res["message"]["content"].strip()
            logger.info(f"Gem Analysis Output: {content}")
            
            for line in content.split("\n"):
                line = line.strip()
                if ":" in line and line != "NONE":
                    parts = line.split(":")
                    ticker = parts[0].strip().replace("$", "").upper()
                    rating = parts[1].strip().upper() if len(parts) > 1 else "LOW"
                    if ticker and len(ticker) <= 10:
                        gems.append({"ticker": ticker, "rating": rating})
        
        return gems

    def simulate_paper_buy(self, ticker: str, rating: str, budget_per_trade: float = 15.0):
        """Simula un acquisto paper per una gemma identificata."""
        if self.virtual_spent + budget_per_trade > self.virtual_budget:
            logger.warning(f"Budget paper esaurito. Spent: {self.virtual_spent}/{self.virtual_budget}")
            return
        
        # Registriamo il paper trade
        trade = {
            "symbol": ticker,
            "entry_time": datetime.now(timezone.utc).isoformat(),
            "budget_eur": budget_per_trade,
            "rating": rating,
            "status": "open",
            "notes": f"Gem Scanner paper trade - Rating: {rating}"
        }
        
        self.paper_trades.append(trade)
        self.virtual_spent += budget_per_trade
        self._save_state()
        logger.info(f"PAPER BUY: {ticker} ({rating}) Budget: {budget_per_trade}€")

    def run_scan_cycle(self):
        """Esegue un ciclo completo di scansione gemme."""
        logger.info("=== GEM SCANNER: Inizio Ciclo ===")
        
        # 1. Scopri trending
        headlines = self.discover_trending_gems()
        logger.info(f"Headlines trovate: {len(headlines)}")
        
        # 2. Valuta con IA
        gems = self.evaluate_gem_potential(headlines)
        logger.info(f"Gemme identificate: {len(gems)}")
        
        # 3. Paper buy delle HIGH rated
        for gem in gems:
            if gem["rating"] == "HIGH":
                self.simulate_paper_buy(gem["ticker"], gem["rating"], budget_per_trade=20.0)
            elif gem["rating"] == "MEDIUM":
                self.simulate_paper_buy(gem["ticker"], gem["rating"], budget_per_trade=10.0)
        
        # 4. Report
        report = {
            "scan_time": datetime.now(timezone.utc).isoformat(),
            "headlines_found": len(headlines),
            "gems_identified": len(gems),
            "gems": gems,
            "paper_portfolio_size": len(self.paper_trades),
            "virtual_spent": self.virtual_spent,
            "virtual_remaining": self.virtual_budget - self.virtual_spent
        }
        
        logger.info(f"=== GEM SCANNER: Ciclo Completato ===")
        return report

    def get_comparison_report(self) -> dict:
        """Genera un report per confronto con il bot DCA principale."""
        return {
            "strategy": "GEM_SCANNER_PAPER",
            "total_trades": len(self.paper_trades),
            "virtual_invested": self.virtual_spent,
            "virtual_remaining": self.virtual_budget - self.virtual_spent,
            "trades": self.paper_trades
        }


if __name__ == "__main__":
    scanner = GemScanner()
    report = scanner.run_scan_cycle()
    print(json.dumps(report, indent=2))
