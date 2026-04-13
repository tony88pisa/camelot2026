# src/ai_trader/strategy/hunter_agent.py
from typing import List, Dict
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.analysis.market_analyzer import MarketAnalyzer
from ai_trader.exchange.binance_adapter import BinanceAdapter

from ai_trader.config.settings import get_settings

logger = get_logger("hunter_agent")

class HunterAgent:
    """
    Gli 'Occhi' dell'AI Trader.
    Scannerizza il mercato Binance alla ricerca di anomalie e opportunit.
    """

    def __init__(self, adapter: BinanceAdapter, analyzer: MarketAnalyzer):
        self.adapter = adapter
        self.analyzer = analyzer
        self.settings = get_settings()

    def identify_opportunities(self, top_n: int = 20, budget: float = None) -> List[Dict]:
        """
        Scannerizza i Top N mercati per volume e identifica le gemme compatibili col budget.
        """
        logger.info(f"Hunter: Inizio scansione Top {top_n} market per opportunit...")
        tickers = self.adapter.get_24h_tickers()
        if not tickers:
            return []

        # Se il budget non  fornito, usa quello dei settings come fallback
        current_budget = (budget if budget is not None else self.settings.INITIAL_CAPITAL) * 0.95
        
        # Filtro: Solo la valuta di base (es. EUR), Volume > 500k, escludi altre Stablecoins
        base = self.settings.QUOTE_CURRENCY
        eligible_pairs = [
            t for t in tickers 
            if t['symbol'].endswith(base) 
            and float(t['quoteVolume']) > 500000
            and not any(x in t['symbol'] for x in ["USDC", "FDUSD", "TUSD", "USDT"])
        ]

        # Ordina per volume decrescente
        eligible_pairs.sort(key=lambda x: float(x['quoteVolume']), reverse=True)
        top_candidates = eligible_pairs[:top_n]

        results = []
        for cand in top_candidates:
            symbol = cand['symbol']
            
            # Verifica Minimo Ordine (Notional) - v7.0.1
            symbol_info = self.adapter.get_symbol_info(symbol)
            min_notional = 10.0 # Fallback prudenziale
            if symbol_info:
                notional_filter = next((f for f in symbol_info.get('filters', []) if f['filterType'] in ['NOTIONAL', 'MIN_NOTIONAL']), None)
                if notional_filter:
                    min_notional = float(notional_filter.get('minNotional', 10.0))
            
            # Se il minimo di Binance  superiore al nostro budget reale, scartiamo la preda
            if current_budget < min_notional:
                logger.warning(f"Hunter: Scartato {symbol} - Richiede {min_notional} EUR (Budget Reale: {current_budget:.2f} EUR)")
                continue

            analysis = self.analyzer.analyze(symbol)
            if analysis.ok:
                # Criteri Hunter: RSI basso (ipervenduto) o Hunter Score alto (anomalia volume)
                score = analysis.hunter_score
                if analysis.rsi < 30 or score > 0.6:
                    results.append({
                        "symbol": symbol,
                        "rsi": analysis.rsi,
                        "hunter_score": score,
                        "recommendation": analysis.recommendation,
                        "price": analysis.price,
                        "volume_ratio": analysis.volume_ratio,
                        "min_notional": min_notional
                    })
        
        # Ordina per Hunter Score
        results.sort(key=lambda x: x['hunter_score'], reverse=True)
        logger.info(f"Hunter: Scansione completata. {len(results)} opportunit identificate.")
        return results

    def get_dynamic_whitelist(self, current_whitelist: List[str], max_hunt: int = 2) -> List[str]:
        """
        Suggerisce una whitelist aggiornata basata sulle migliori prede trovate.
        """
        opps = self.identify_opportunities()
        new_whitelist = list(current_whitelist) # Mantieni le basi (es BTC)
        
        added = 0
        for opt in opps:
            if opt['symbol'] not in new_whitelist:
                new_whitelist.append(opt['symbol'])
                added += 1
            if added >= max_hunt: break
            
        # Limita la whitelist totale per non sforare il budget di 30 (max 3 monete totali)
        return new_whitelist[:3]
