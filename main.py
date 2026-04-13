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
from ai_trader.risk.risk_kernel import RiskKernel
from ai_trader.risk.risk_state_tracker import RiskStateTracker

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
        self.adapter = BinanceAdapter(mode=self.mode) 
        self.risk_tracker = RiskStateTracker() # v12.0: Memoria di Rischio Integrata
        
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

    def _verify_live_readiness(self) -> dict:
        """
        Gating di sicurezza obbligatorio per la modalit LIVE.
        Restituisce un report di readiness con i motivi di eventuale blocco.
        """
        report = {"ok": True, "errors": []}
        
        # 1. LIVE mode check
        if self.mode != "live":
            # Se siamo in dry_run/testnet, i gate sono meno stringenti
            return report

        # 2. Credenziali Presence
        if not self.adapter.api_key or not self.adapter.api_secret:
            report["errors"].append("CREDENTIALS_MISSING")
            
        # 3. Exchange Health
        health = self.adapter.health_check()
        if not health["ok"]:
            report["errors"].append(f"EXCHANGE_UNHEALTHY: {health.get('status')}")

        # 4. Whitelist Integrity (Staging Rule: BTCUSDT only for now)
        if len(self.settings.WHITELIST_PAIRS) != 1 or "BTCUSDT" not in self.settings.WHITELIST_PAIRS:
            report["errors"].append("WHITELIST_NOT_RESTRICTED_TO_BTCUSDT")

        # 5. Risk Kernel & Tracker Check
        if not self.risk_kernel or not self.risk_tracker:
            report["errors"].append("RISK_SYSTEM_NOT_INITIALIZED")
            
        # 6. Budget Integrity (Settled Balance only)
        summary = self.adapter.get_account_summary()
        current_balance = summary.get("free_quote_balance", 0.0)
        if current_balance <= 0:
            report["errors"].append("ZERO_SETTLED_BALANCE")

        if report["errors"]:
            report["ok"] = False
        
        return report

    def _apply_capital_discipline(self, budget: float) -> float:
        """Applica i limiti di sicurezza al budget live (v12.0)."""
        if self.mode == "live":
            # Cap a 24 EUR (approx 25 USDT) o 50% saldo (il minore)
            max_allowed = min(budget * 0.5, 25.0)
            logger.info(f"CAPITAL GUARD: Live budget capped at {max_allowed:.2f} USDT")
            return max_allowed
        return budget

    async def boot_sequence(self):
        """Sequenza di avvio sicura v12.0 con Live Readiness Gate."""
        print(f"[v12.0] AVVIO APEX REACTOR... (Mode: {self.mode})")
        
        # 1. Inizializzazione Risk Kernel
        self.risk_kernel = RiskKernel()

        # 2. Avvio Streaming Core
        await self.streamer.start()
        
        # 3. Sottoscrizione Pairs (Whitelist)
        whitelist = self.settings.WHITELIST_PAIRS
        for symbol in whitelist:
            await self.streamer.subscribe_depth(symbol)
            
        # 4. Sincronizzazione Saldo Reale (Sovereign Holism)
        summary = self.adapter.get_account_summary()
        self.current_live_budget = summary.get("free_quote_balance", 0.0)
        self.risk_tracker.initialize_from_summary(summary)
        
        # 5. LIVE READINESS GATE (BLOCKING)
        readiness = self._verify_live_readiness()
        if not readiness["ok"]:
            logger.error(f"FATAL: Live Readiness Gate FAILED: {readiness['errors']}")
            print(f"!!! EMERGECY STOP: Readiness Errors: {readiness['errors']}")
            await self.shutdown_sequence()
            sys.exit(1)
            
        # 6. Capital Discipline (v12.0)
        self.current_live_budget = self._apply_capital_discipline(self.current_live_budget)

        # 7. Neural Heat-Up (v11.3 Titan Brain)
        logger.info(f"Titan Brain: Risveglio neurale su GPU (Modello: {self.ollama.model})...")
        if self.ollama.health_check():
            self.ollama.chat([{"role": "user", "content": "wake up"}], max_tokens=5)
        else:
            logger.warning("Titan Brain: Ollama non risponde.")
            
        self.running = True
        logger.info("ApexReactor: Sequenza di Avvio Completata con Successo.")

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
        """Esecuzione market con protezione deterministica Iron Core v12.0 e Risk Kernel."""
        symbol = action["symbol"]
        side = action["action"]
        raw_qty = action.get("usdt_amount") if side == "BUY" else action.get("quantity")
        
        # 1. RISK KERNEL BARRIER (FASE 2 - Sovranit del Rischio)
        # Costruzione Intento per il Tribunale Supremo
        from ai_trader.risk.policy_models import TradeIntent, PortfolioState, SystemState
        import time

        risk_kernel = RiskKernel() 
        
        # Recupero Stato Portafoglio e Sistema REALE (Snapshot v12.0)
        portfolio = self.risk_tracker.get_portfolio_state()
        system = self.risk_tracker.get_system_state()

        intent = TradeIntent(
            symbol=symbol,
            side=side,
            proposed_notional=raw_qty if side == "BUY" else (raw_qty * self.adapter.get_ticker_price(symbol).get("price", 0.0)),
            proposed_quantity=raw_qty if side == "SELL" else 0.0,
            signal_quality=0.90, # Default high for manual/grid triggers
            timestamp=time.time()
        )

        risk_decision = risk_kernel.evaluate_intent(intent, portfolio, system)
        
        if not risk_decision.allowed:
            self.risk_tracker.record_risk_block(risk_decision.reason_codes[0])
            logger.warning(f"RISK KERNEL BLOCK: {risk_decision.reason_codes} ({symbol} {side} Snapshot: {risk_decision.risk_snapshot})")
            return

        # 2. Pre-flight Normalizzatore (Sovereign Protection - FASE 1)
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
                    # Registrazione nel Tracker (State Hardening)
                    self.risk_tracker.record_order_fill(symbol, side, (executed_qty * avg_price), executed_qty)
                    
                    if side == "BUY":
                        self.grid_engine.record_buy(symbol, action["level_index"], avg_price, executed_qty)
                    else:
                        self.grid_engine.record_sell(symbol, action["level_index"], avg_price, executed_qty)
                    logger.info(f"APEX ORDER SUCCESS: {symbol} {side} Filled: {executed_qty} @ {avg_price}")
                else:
                    self.risk_tracker.record_order_failure("zero_fill")
                    logger.error(f"APEX RECONCILIATION FAILURE: {symbol} Fill nullo. Status: {order.get('status')}")
            else:
                self.risk_tracker.record_order_failure("rejected")
                logger.error(f"APEX EXECUTION REJECTED: {symbol} Error: {order.get('error')}")
                
        except Exception as e:
            self.risk_tracker.record_order_failure("crash")
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
