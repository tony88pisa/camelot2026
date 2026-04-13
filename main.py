# main.py
# 2026-04-13 - Apex Predator v11.0: High-Frequency Async Reactor Core
"""
QUANTUM HUNTER v11.0 - APEX PREDATOR Edition
Il culmine dell'ingegneria finanziaria autonoma. 
Architettura asincrona, event-driven, con sensing L2 e regime-awareness.
"""

import asyncio
import argparse
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Import moduli interni con sintassi 2026
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.config import settings
from ai_trader.exchange.binance_adapter import BinanceAdapter
from ai_trader.exchange.binance_streamer import BinanceStreamer
from ai_trader.analysis.market_analyzer import MarketAnalyzer
from ai_trader.strategy.grid_engine import GridEngine, GridConfig
from ai_trader.strategy.hunter_agent import HunterAgent
from ai_trader.risk.paladin_agent import PaladinAgent
from ai_trader.agents.whale_watch_agent import WhaleWatchAgent
from ai_trader.agents.regime_shift_agent import RegimeShiftAgent
from ai_trader.brain.brain_runtime import BrainRuntime
from ai_trader.brain.brain_types import BrainContext # v11.4: Import context types
from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.core.ollama_client import OllamaClient

logger = get_logger("main_reactor")

class ApexReactor:
    """
    Il cuore pulsante del bot v11.0. 
    Coordina flussi di dati, agenti e strategie in modalit asincrona.
    """
    
    def __init__(self, mode: str = "mainnet", interval: int = 60):
        self.mode = mode
        self.interval = interval
        self.running = False
        self.settings = settings.get_settings()
        
        # Inizializzazione Sottosistemi
        self.adapter = BinanceAdapter(mode=self.mode) # v11.1: Fix propagazione modo
        
        # v11.1: Iniezione credenziali nello streamer per snapshots reali
        self.streamer = BinanceStreamer(
            api_key=self.adapter.api_key or "", 
            api_secret=self.adapter.api_secret or ""
        )
        
        self.analyzer = MarketAnalyzer(self.adapter)
        self.grid_engine = GridEngine()
        self.episode_store = EpisodeStore()
        
        # Inizializzazione Agenti
        self.hunter = HunterAgent(self.adapter, self.analyzer)
        self.paladin = PaladinAgent(self.adapter)
        self.whale_watch = WhaleWatchAgent()
        self.regime_shift = RegimeShiftAgent()
        
        # v11.3: Titan Brain Configuration
        self.ollama = OllamaClient()
        
        # v11.4: Creazione Context Professionale per il Brain
        ctx = BrainContext(
            settings=self.settings,
            exchange_adapter=self.adapter,
            strategy_engine=self.grid_engine,
            logger=logger,
            ollama_client=self.ollama, # Link IA
            now_fn=lambda: datetime.now().isoformat()
        )
        self.brain = BrainRuntime(ctx) 
        
        logger.info(f"ApexReactor v11.0 Inizializzato (Modo: {self.mode})")

    async def boot_sequence(self):
        """Sequenza di avvio sicura v11.0."""
        print("[v11.0] AVVIO APEX REACTOR... (Aprile 2026 Status)")
        
        # 1. Avvio Streaming Core
        await self.streamer.start()
        
        # 2. Sottoscrizione Pairs (Whitelist)
        whitelist = self.settings.WHITELIST_PAIRS
        for symbol in whitelist:
            await self.streamer.subscribe_depth(symbol)
            
        # 3. Sincronizzazione Saldo Reale (Sovereign Holism)
        summary = self.adapter.get_account_summary()
        self.current_live_budget = summary.get("free_quote_balance", 0.0)
        print(f"I  [SYSTEM] Saldo Iniziale Sincronizzato: {self.current_live_budget:.2f} {self.settings.QUOTE_CURRENCY}")
        
        # 4. Neural Heat-Up (v11.3 Titan Brain)
        logger.info(f"Titan Brain: Risveglio neurale su GPU (Modello: {self.ollama.model})...")
        if self.ollama.health_check():
            # Warm-up call per caricare il modello in VRAM
            self.ollama.chat([{"role": "user", "content": "wake up"}], max_tokens=5)
            logger.info("Titan Brain: Modello caricato con successo in VRAM.")
        else:
            logger.warning("Titan Brain: Ollama non risponde. Procedo in modalita euristica.")
            
        logger.info("ApexReactor: Sequenza di Avvio Completata con Successo.")
        
        self.running = True

    async def shutdown_sequence(self):
        """Arresto controllato."""
        self.running = False
        await self.streamer.stop()
        logger.info("ApexReactor: Shutdown completato.")

    async def process_cycle(self):
        """Ciclo principale di analisi e reazione."""
        whitelist = self.settings.WHITELIST_PAIRS
        
        # v11.0: Calcolo budget per l'intero portfolio (Interest Compounding)
        overall = self.grid_engine.get_overall_status()
        active_capital = self.current_live_budget + overall.get("total_profit", 0.0) # v11.4: Fix EUR naming
        
        for symbol in whitelist:
            try:
                # 1. Recupero Microstruttura L2 (Real-time)
                order_book = self.streamer.get_order_book(symbol)
                if not order_book:
                    continue # Attesa sincronizzazione

                # 2. Analisi Whale & OBI
                whale_data = self.whale_watch.analyze_order_book(order_book)
                whale_signal = self.whale_watch.get_predator_signal(order_book)
                
                # 3. Analisi Tecnica Snapshot
                tech_analysis = self.analyzer.analyze(symbol)
                if not tech_analysis.ok: continue
                
                # 4. Determinazione Regime di Mercato (AI GEAR-SHIFT)
                current_regime = self.regime_shift.detect_regime(
                    {"trend_score": tech_analysis.trend_score, 
                     "volatility_score": tech_analysis.volatility_score,
                     "rsi": tech_analysis.rsi},
                    whale_signal
                )
                strategy_adj = self.regime_shift.get_strategy_adjustments()

                # 5. Gestione Griglia Apex
                await self._manage_grid_apex(symbol, tech_analysis, whale_data, current_regime, active_capital)

            except Exception as e:
                logger.error(f"Errore Ciclo Apex su {symbol}", error=str(e))
                await asyncio.sleep(2)

    async def _manage_grid_apex(self, symbol, tech, whale, regime, total_cap):
        """Gestione avanzata della griglia basata su regime e balene."""
        # Se la griglia non esiste, consultiamo il Brain v11.0
        if symbol not in self.grid_engine.grids:
            budget = (total_cap / len(self.settings.WHITELIST_PAIRS)) * regime.risk_level
            
            # Brain Decision (v11.0 incorpored Whale Signal)
            decision = self.brain.evaluate_strategy(symbol, budget)
            if not decision["ok"] and "WHALE" not in whale.get("pressure", ""):
                # Se il brain dice no E non ci sono balene a supporto, saltiamo
                return

            # Configurazione griglia v11.0 (Adattiva)
            grid_config = GridConfig(
                symbol=symbol,
                lower_price=tech.price * (1 - (0.01 * regime.max_drawdown_limit)),
                upper_price=tech.price * (1 + (0.01 * regime.tp_multiplier)),
                num_levels=self.settings.GRID_LEVELS,
                budget_usdt=budget
            )
            self.grid_engine.setup_grid(grid_config)

        # Valutazione con TP Dinamico Apex
        current_price = tech.price
        tp_target = tech.recommended_tp_pct * regime.tp_multiplier
        
        actions = self.grid_engine.evaluate(symbol, current_price, min_profit_pct=tp_target)
        for action in actions:
            await self._execute_apex_order(action)

    def _pre_flight_check_order(self, symbol, side, qty, price=0.0):
        """
        Validazione deterministica e normalizzazione pre-esecuzione v12.0.
        Restituisce un payload con i valori snappati pronti per l'invio.
        """
        result = {
            "ok": False,
            "normalized_qty": 0.0,
            "normalized_price": 0.0,
            "error": None,
            "filters": {}
        }

        # 1. Verifica Whitelist
        if symbol not in self.settings.WHITELIST_PAIRS:
            result["error"] = f"Simbolo {symbol} non in whitelist"
            return result
            
        # 2. Verifica Stato Adapter
        health = self.adapter.health_check()
        if not health["ok"] or health["status"] == "unavailable":
            result["error"] = "Adapter Exchange non raggiungibile"
            return result
            
        # 3. Recupero Regole e Snapping
        rules = self.adapter.get_symbol_rules(symbol)
        if not rules:
            result["error"] = f"Impossibile recuperare regole per {symbol}"
            return result
        result["filters"] = rules

        # Se BUY usiamo quoteOrderQty (USDT). Se SELL normalizziamo la base qty.
        if side == "BUY":
            # Normalizzazione quote (notional) - arrotondamento standard a 2 decimali per USDT
            norm_qty = round(qty, 2) 
            result["normalized_qty"] = norm_qty
            
            # Check Min Notional
            if norm_qty < rules["minNotional"]:
                result["error"] = f"Ordine BUY sotto Min Notional: {norm_qty} < {rules['minNotional']}"
                return result
        else:
            # SELL: Snap della base quantity tramite adapter
            norm_qty = self.adapter.snap_quantity(symbol, qty)
            result["normalized_qty"] = norm_qty
            
            # Check Lot Size
            if norm_qty < rules["minQty"]:
                result["error"] = f"Quantit SELL post-snap inferiore a minQty: {norm_qty} < {rules['minQty']}"
                return result
            
            # Check Notional post-snap
            current_price = self.adapter.get_ticker_price(symbol).get("price", 0.0)
            notional = norm_qty * current_price
            if notional < rules["minNotional"]:
                result["error"] = f"Ordine SELL post-snap sotto Min Notional: {notional:.2f} < {rules['minNotional']}"
                return result

        # 4. Verifica Balance Reale Finale
        summary = self.adapter.get_account_summary()
        if side == "BUY":
            free_balance = summary.get("free_quote_balance", 0.0)
            if result["normalized_qty"] > free_balance:
                result["error"] = f"Saldo insufficiente: richiesti {result['normalized_qty']}, disponibili {free_balance}"
                return result
        else:
            # Per i SELL dovremmo verificare l'asset di base, ma l'adapter attuale 
            # espone principalmente quote balance. Placeholder per futura espansione balance_check.
            pass

        result["ok"] = True
        return result

    async def _execute_apex_order(self, action):
        """Esecuzione market con protezione deterministica Iron Core v12.0."""
        symbol = action["symbol"]
        side = action["action"]
        raw_qty = action.get("usdt_amount") if side == "BUY" else action.get("quantity")
        
        # 1. Pre-flight Normalizzatore (Sovereign Protection)
        guard = self._pre_flight_check_order(symbol, side, raw_qty)
        if not guard["ok"]:
            logger.warning(f"APEX ORDER BLOCKED: {guard['error']} ({symbol} {side})")
            return

        # UTILIZZO VALORI NORMALIZZATI
        exec_qty = guard["normalized_qty"]
        logger.info(f"APEX ORDER DISPATCH: {side} {symbol} (Normalized Qty: {exec_qty})")
        
        try:
            # Invio all'adapter
            order = self.adapter.place_market_order(symbol, side, exec_qty)
            
            # 2. Riconciliazione Finale (Fase 1 Hardening)
            if order.get("ok"):
                # Validazione Fill Reali
                executed_qty = float(order.get("executed_qty", 0.0))
                avg_price = float(order.get("avg_price", 0.0))
                
                if executed_qty > 0 and avg_price > 0:
                    if side == "BUY":
                        self.grid_engine.record_buy(symbol, action["level_index"], avg_price, executed_qty)
                    else:
                        self.grid_engine.record_sell(symbol, action["level_index"], avg_price, executed_qty)
                    logger.info(f"APEX ORDER SUCCESS: {symbol} {side} Filled: {executed_qty} @ {avg_price}")
                else:
                    logger.error(f"APEX RECONCILIATION FAILURE: {symbol} Ordine OK ma fill nullo. Status: {order.get('status')}")
            else:
                logger.error(f"APEX EXECUTION REJECTED: {symbol} Error: {order.get('error')}")
                
        except Exception as e:
            logger.error(f"APEX CRITICAL CRASH: Order {symbol}", error=str(e))

    async def run(self):
        """Reattore principale."""
        # v11.2: Hardcoding forzato whitelist per stabilita assoluta
        self.settings.WHITELIST_PAIRS = ["SOLEUR", "BTCEUR"]
        logger.info(f"v11.2 Tabula Rasa: Whitelist HARDCODED: {self.settings.WHITELIST_PAIRS}")
        
        await self.boot_sequence()
        
        cycle_count = 0
        while self.running:
            cycle_count += 1
            print(f"\n[APEX CYCLE #{cycle_count}] --- {datetime.now().strftime('%H:%M:%S')}")
            
            # 1. Check Salute Paladin (v11.0 priority)
            health = self.paladin.check_portfolio_health()
            print(f"I  Paladin: Status={health['status']} | Equity={health.get('equity', 0):.2f} | DD={health.get('drawdown', 0):.2f}%")
            
            # 2. Processo strategico
            await self.process_cycle()
            
            # 3. AI Heartbeat & Dream (Ogni 10 cicli)
            if cycle_count % 10 == 0:
                print("[HEARTBEAT] Mantengo Titan Brain caldo in VRAM...")
                # Una piccola chat per impedire ad Ollama di scaricare il modello
                self.ollama.chat([{"role": "user", "content": "keepalive"}], max_tokens=1)
                print("[DREAM] Avvio Riflessione MAD v11.0...")
            
            await asyncio.sleep(self.interval)

async def main_async():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="mainnet")
    parser.add_argument("--interval", type=float, default=60)
    args = parser.parse_args()
    
    reactor = ApexReactor(mode=args.mode, interval=args.interval)
    try:
        await reactor.run()
    except KeyboardInterrupt:
        logger.info("ApexReactor: Arresto manuale rilevato (KeyboardInterrupt)")
        await reactor.shutdown_sequence()
    except Exception as e:
        logger.critical(
            "!!! CRASH REACTOR v11.0 !!!",
            error=str(e),
            trace=traceback.format_exc()
        )
        await reactor.shutdown_sequence()

if __name__ == "__main__":
    asyncio.run(main_async())
