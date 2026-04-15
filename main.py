# main.py
# 2026-04-14 - Apex Predator v13.0: DCA Intelligent + RAG Sentiment
"""
QUANTUM HUNTER v13.0 - DCA INTELLIGENT Edition
Strategia DCA potenziata dal Sentiment RAG (gemma2:2b).
Compra sulla paura, vendi sull'avidità. Grid mantenuta per sell management.
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
from ai_trader.strategy.dca_engine import DCAEngine, DCAAction
from ai_trader.strategy.hunter_agent import HunterAgent
from ai_trader.risk.paladin_agent import PaladinAgent
from ai_trader.agents.whale_watch_agent import WhaleWatchAgent
from ai_trader.agents.regime_shift_agent import RegimeShiftAgent
from ai_trader.strategy.tactical_commander import TacticalCommander
from ai_trader.brain.brain_runtime import BrainRuntime
from ai_trader.brain.brain_types import BrainContext # v11.4: Import context types
from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.core.ollama_client import OllamaClient
from ai_trader.risk.risk_kernel import RiskKernel
from ai_trader.risk.risk_state_tracker import RiskStateTracker
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.risk.opportunity_models import OpportunityCandidate, QualityScore, StructuredRejectedTrade
from ai_trader.risk.friction_brain import FrictionBrain
from ai_trader.risk.opportunity_arbiter import OpportunityArbiter
from ai_trader.risk.capital_allocator import CapitalAllocator
from ai_trader.risk.portfolio_router import PortfolioRouter
from ai_trader.risk.outcome_evaluator import OutcomeEvaluator
from ai_trader.risk.night_session import NightSession, NightSessionConfig

logger = get_logger("main_reactor")

class ApexReactor:
    """
    Il cuore pulsante del bot v11.0. 
    Coordina flussi di dati, agenti e strategie in modalit asincrona.
    """
    
    def __init__(self, mode: str = "mainnet", interval: int = 60, target_symbols: list[str] = None, max_positions: int = 1, night_mode: bool = False):
        self.mode = mode
        self.interval = interval
        self.target_symbols = target_symbols or ["BTCUSDT"]
        self.max_positions = max_positions
        self.night_mode = night_mode
        self.running = False
        self.settings = settings.get_settings()
        
        # Inizializzazione Sottosistemi
        self.adapter = BinanceAdapter(mode=self.mode) 
        self.lesson_store = LessonStore()
        self.risk_tracker = RiskStateTracker(lesson_store=self.lesson_store)
        
        # v12.0: Fase 6 & 7 - Economic & Learning Layer
        self.friction_brain = FrictionBrain()
        self.arbiter = OpportunityArbiter()
        self.allocator = CapitalAllocator()
        self.portfolio_router = PortfolioRouter()
        self.outcome_evaluator = OutcomeEvaluator()
        self.rejection_review_counter = 0
        self.night_session = None  # Initialized in run() if overnight mode
        
        # v11.1: Iniezione credenziali nello streamer per snapshots reali
        self.streamer = BinanceStreamer(
            api_key=self.adapter.api_key or "", 
            api_secret=self.adapter.api_secret or ""
        )
        
        from ai_trader.analysis.sentiment_connector import SentimentConnector
        
        self.analyzer = MarketAnalyzer(self.adapter)
        self.grid_engine = GridEngine()
        self.episode_store = EpisodeStore()
        
        # v13.0: DCA Intelligent Engine (strategia primaria)
        self.dca_engine = DCAEngine(base_tranche_eur=12.0, cooldown_minutes=15)
        self.sentiment = SentimentConnector(supermemory=self.episode_store)
        
        # Inizializzazione Agenti
        self.hunter = HunterAgent(self.adapter, self.analyzer)
        self.paladin = PaladinAgent(self.adapter)
        self.whale_watch = WhaleWatchAgent()
        self.regime_shift = RegimeShiftAgent()
        self.tactical_commander = TacticalCommander()
        
        # v11.3: Titan Brain Configuration (Optional - deterministic mode if unavailable)
        self.ollama = OllamaClient()
        self.ollama_available = False
        
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

        # 4. Whitelist Integrity
        current_symbols = set(self.settings.WHITELIST_PAIRS)
        if not current_symbols:
            report["errors"].append("WHITELIST_EMPTY")

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
        
        # 1. Recupero Stato da Memoria Persistente (v12.0)
        self.risk_tracker.restore_recent_incident_state()
        
        # 2. Inizializzazione Risk Kernel
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

        # 7. Neural Heat-Up (v11.3 Titan Brain - Optional)
        try:
            if self.ollama.health_check():
                self.ollama.chat([{"role": "user", "content": "wake up"}], max_tokens=5)
                self.ollama_available = True
                logger.info(f"Titan Brain ONLINE: {self.ollama.model}")
            else:
                logger.warning("Ollama unavailable — deterministic mode active")
        except Exception as e:
            logger.warning(f"Ollama init failed: {e} — deterministic mode active")
            
        self.running = True
        logger.info("ApexReactor: Sequenza di Avvio Completata con Successo.")

    async def shutdown_sequence(self):
        """Arresto controllato."""
        self.running = False
        await self.streamer.stop()
        logger.info("ApexReactor: Shutdown completato.")

    async def process_cycle(self):
        """Ciclo principale v13.0: DCA Intelligent + RAG Sentiment."""
        # Night Session hard stop check
        if self.night_session and self.night_session.is_halted:
            logger.warning(f"NightSession HALTED: {self.night_session.halt_reason}. Skipping cycle.")
            return

        summary = self.adapter.get_account_summary()
        active_capital = summary.get("free_quote_balance", 0.0)
        
        # === AUTONOMOUS LIQUIDITY RECOVERY (v14.0) ===
        if active_capital < 6.0:
            await self._scavenge_liquidity(summary)
            # Ricarica i saldi dopo il recovery
            summary = self.adapter.get_account_summary()
            active_capital = summary.get("free_quote_balance", 0.0)

        self.risk_tracker.initialize_from_summary(summary)

        # === DCA INTELLIGENT LOOP (v14.0 Hybrid MoE - Sovereign Hunter) ===
        best_action: DCAAction | None = None
        best_confidence = -1.0

        # Disattiva Whitelist: Lascia che Hunter esplori le top 15 monete per volume
        opportunities = self.hunter.identify_opportunities(top_n=15, budget=active_capital)
        target_symbols = [opp["symbol"] for opp in opportunities]
        
        # Aggiungi le monete in cui siamo già esposti per non perdere le finestre di TAKE_PROFIT
        for sym, pos in self.dca_engine.positions.items():
            if pos.total_qty > 0 and sym not in target_symbols:
                target_symbols.append(sym)

        logger.info(f"Hunter Scavenger attivo: Valutazione di {len(target_symbols)} mercati autonomamente.")

        for symbol in target_symbols:
            # 1. Fetch Dati Dai Sensori
            rag = self.sentiment.get_market_sentiment(symbol)
            sentiment_label = rag.get("label", "NEUTRAL")
            
            ticker = self.adapter.get_ticker_price(symbol)
            current_price = ticker.get("price", 0.0)
            if current_price <= 0:
                continue
                
            order_book = self.adapter.get_order_book(symbol)
            if not order_book:
                continue
                
            tech = self.analyzer.analyze(symbol)
            if not tech.ok:
                continue
                
            whale_data = self.whale_watch.analyze_order_book(order_book)
            whale_signal = self.whale_watch.get_predator_signal(order_book)
            regime = self.regime_shift.detect_regime(
                {"trend_score": tech.trend_score, "volatility_score": tech.volatility_score}, 
                whale_signal
            )

            # 2. Sintesi del Cervello Tattico (Gemma2:2b Caveman mode)
            tactical_cmd = self.tactical_commander.evaluate_tactical_state(
                symbol=symbol,
                sentiment=sentiment_label,
                whale=whale_data,
                regime=regime.name,
                tech={"rsi": tech.rsi, "trend_score": tech.trend_score}
            )

            # 3. Trasformazione matematica deterministica (Esecutore DCA)
            dca_action = self.dca_engine.evaluate(
                symbol=symbol,
                current_price=current_price,
                tactical_command=tactical_cmd,
                free_balance_eur=active_capital,
                tp_pct=5.0
            )

            logger.info(f"DCA [{symbol}]: {dca_action.action} | {dca_action.reason} | Confidence: {dca_action.confidence:.2f}")

            # 4. Seleziona l'azione con confidenza massima
            if dca_action.action in ["BUY", "SELL"] and dca_action.confidence > best_confidence:
                best_action = dca_action
                best_confidence = dca_action.confidence

        # 5. Esegui la migliore azione DCA trovata
        if best_action:
            await self._execute_dca_order(best_action)
        else:
            logger.info("DCA CYCLE: Nessuna azione qualificata. HOLD su tutte le posizioni.")

        # Review a T+60m per Counterfactual Learning
        self._maybe_evaluate_past_rejections()

    async def _scavenge_liquidity(self, summary: dict):
        """
        Scansiona il wallet e vende i residui non whitelistati (es. vecchi PEPE/ADA)
        se il valore supera il minimo di Binance (5.5€) per finanziare le operazioni DCA.
        """
        # Estrai i nomi base delle coin DCA salvate + posizioni attive del Hunter
        core_assets = set(p.replace("EUR", "").replace("USDT", "") for p in self.settings.WHITELIST_PAIRS)
        # Proteggi anche le coin in cui il DCA Engine ha posizioni aperte
        for sym in self.dca_engine.positions:
            base = sym.replace("EUR", "").replace("USDT", "")
            core_assets.add(base)
        
        balances = summary.get("balances", [])
        prices = self.adapter.get_all_prices()
        
        for b in balances:
            asset = b["asset"]
            free_qty = float(b["free"])
            
            if free_qty <= 0:
                continue
            
            # Non toccare valute Fiat o Monete Core del DCA/Hunter
            if asset in ["EUR", "USDT"] or asset in core_assets:
                continue
                
            # Calcola il controvalore in EUR
            symbol = f"{asset}EUR"
            eur_val = 0.0
            if symbol in prices:
                eur_val = free_qty * prices[symbol]
            elif f"{asset}USDT" in prices and "USDTEUR" in prices:
                eur_val = free_qty * prices[f"{asset}USDT"] * prices["USDTEUR"]
                
            if eur_val > 5.5:
                # Binance supporta vendite sopra i 5.0€ circa
                logger.warning(
                    f"DCA EMERGENCY LIQUIDATION: Vendo legacy asset {asset} "
                    f"(valore: {eur_val:.2f} EUR) per recuperare liquidit\u00e0."
                )
                action = {
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": free_qty,
                    "level_index": None
                }
                # Delega all'adapter via pipeline principale per accounting e validazione
                await self._execute_apex_order(action)

    async def _evaluate_symbol_decision(self, symbol, total_cap):
        """Valuta economicamente un singolo simbolo senza eseguire azioni."""
        order_book = self.adapter.get_order_book(symbol)
        if not order_book:
            return None
        tech = self.analyzer.analyze(symbol)
        if not tech.ok:
            return None
        whale = self.whale_watch.analyze_order_book(order_book)
        whale_signal = self.whale_watch.get_predator_signal(order_book)
        
        regime = self.regime_shift.detect_regime(
            {"trend_score": tech.trend_score, "volatility_score": tech.volatility_score}, whale_signal
        )
        tp_target = tech.recommended_tp_pct * regime.tp_multiplier
        if symbol not in self.grid_engine.grids:
            # Use max_positions for budget slicing so each grid level clears the 1.5 USDT dust filter
            budget_cap = (total_cap / max(1, self.max_positions)) * regime.risk_level
            grid_config = GridConfig(
                symbol=symbol,
                lower_price=tech.price * (1 - (0.01 * regime.max_drawdown_limit)),
                upper_price=tech.price * (1 + (0.01 * regime.tp_multiplier)),
                num_levels=self.settings.GRID_LEVELS,
                budget_usdt=budget_cap
            )
            self.grid_engine.setup_grid(grid_config)
            
        actions = self.grid_engine.evaluate(symbol, tech.price, min_profit_pct=tp_target)
        if not actions:
            return None

        candidates, friction_reports = [], []
        for action in actions:
            if action["action"] not in ["BUY", "SELL"]:
                continue
            cand = OpportunityCandidate(
                symbol=symbol, side=action["action"], entry_price=tech.price,
                expected_edge_pct=tp_target / 100,
                signal_strength=whale.get("signal_strength", 0.7),
                regime=regime.name, volatility_score=tech.volatility_score,
                source="grid_apex",
            )
            fric = self.friction_brain.estimate_friction(
                symbol, order_book, action.get("usdt_amount", 15.0)
            )
            candidates.append(cand)
            friction_reports.append(fric)
        return self.arbiter.evaluate_candidates(candidates, friction_reports)

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

        # 5. Arbitraggio Economico v12.0 (Phase 6)
        # Convertiamo le azioni in candidati per l'Arbiter
        candidates = []
        friction_reports = []
        
        # Recuperiamo Order Book fresco per Friction Brain
        order_book = self.adapter.get_order_book(symbol)
        
        current_price = tech.price
        actions = self.grid_engine.evaluate(symbol, current_price, min_profit_pct=regime.tp_multiplier)
        if not actions:
            return
            
        for action in actions:
            if action["action"] not in ["BUY", "SELL"]: continue
            
            # Stima Edge: Per la griglia, l'edge atteso è il TP target PCT
            tp_target = tech.recommended_tp_pct * regime.tp_multiplier
            expected_edge = tp_target / 100.0
            
            # Fetch Daemon RAG sentiment instantly from memory
            rag_sentiment = self.sentiment.get_market_sentiment(symbol)
            rag_score = rag_sentiment.get("sentiment_score", 0.5)
            
            # Blend whale pressure with background RAG intelligence
            base_signal = whale.get("signal_strength", 0.7)
            blended_signal = (base_signal * 0.7) + (rag_score * 0.3)
            
            cand = OpportunityCandidate(
                symbol=symbol,
                side=action["action"],
                entry_price=current_price,
                expected_edge_pct=expected_edge,
                signal_strength=blended_signal,
                regime=regime.name,
                volatility_score=tech.volatility_score,
                source="grid_apex",
                metadata={"level_index": action.get("level_index"), "rag_label": rag_sentiment.get("label")}
            )
            
            # Calcolo Friction
            fric = self.friction_brain.estimate_friction(symbol, order_book, action.get("usdt_amount", 15.0))
            
            candidates.append(cand)
            friction_reports.append(fric)

        # 6. Selezione e Allocazione
        arb_decision = self.arbiter.evaluate_candidates(candidates, friction_reports)
        
        if arb_decision.allowed:
            # Recuperiamo saldo reale per l'allocatore
            summary = self.adapter.get_account_summary()
            balance = summary.get("free_quote_balance", 0.0)
            
            allocation = self.allocator.allocate(arb_decision, balance)
            
            if allocation.action != "NO_TRADE":
                # Aggiorniamo l'azione originale con il nuovo notional allocato
                # Per ora semplifichiamo: prendiamo la prima azione approvata
                final_action = next(a for a in actions if a["action"] == allocation.action)
                final_action["usdt_amount"] = allocation.allocated_notional
                
                logger.info(f"ECONOMIC APPROVAL: {symbol} {allocation.action} Q:{arb_decision.quality.value} NetEdge:{arb_decision.net_edge_pct:.4f} Alloc:{allocation.allocated_notional:.2f}")
                await self._execute_apex_order(final_action)
            else:
                logger.warning(f"ALLOCATION REJECTED: {symbol} Reason: {allocation.reason}")
        else:
            # Registrazione Counterfactual Memory per i rifiuti dell'Arbiter
            if arb_decision.candidate:
                self.risk_tracker.emit_counterfactual_lesson(None, arb_decision)
                logger.info(f"ECONOMIC REJECTION: {symbol} Quality:{arb_decision.quality.value} Reason:{arb_decision.reason_codes}")

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

        # 1. Verifica Simbolo Autorizzato (Sovereign Hunter v14.0)
        # Permetti: Whitelist statica + qualsiasi coin in portafoglio DCA attivo
        allowed_symbols = set(self.settings.WHITELIST_PAIRS)
        allowed_symbols.update(self.dca_engine.positions.keys())
        if symbol not in allowed_symbols:
            # Ultima chance: se è una coppia EUR valida su Binance, lasciala passare
            symbol_info = self.adapter.get_symbol_info(symbol)
            if not symbol_info:
                result["error"] = f"Simbolo {symbol} non riconosciuto su Binance"
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

    async def _allocate_and_execute(self, arb_decision, balance):
        """Esegue l'allocazione e l'ordine finale."""
        allocation = self.allocator.allocate(arb_decision, balance)
        if allocation.action != "NO_TRADE":
            symbol = arb_decision.candidate.symbol
            notional = allocation.allocated_notional
            sig_quality = arb_decision.candidate.signal_strength

            # Night Session gate
            if self.night_session:
                allowed, reason = self.night_session.check_trade_allowed(symbol, notional, sig_quality)
                if not allowed:
                    logger.info(f"NightSession BLOCKED trade: {reason}")
                    self.night_session.record_rejection(symbol, reason)
                    self._handle_rejection(arb_decision, mode=f"NIGHT_BLOCK:{reason}")
                    return

            action = {
                "symbol": symbol,
                "action": allocation.action,
                "usdt_amount": notional,
                "level_index": arb_decision.candidate.metadata.get("level_index")
            }
            await self._execute_apex_order(action)

            # Night Session tracking
            if self.night_session:
                self.night_session.record_trade_executed(symbol, allocation.action, notional)
        else:
            self._handle_rejection(arb_decision, mode="LOW_ALLOCATION")

    async def _execute_dca_order(self, dca_action: DCAAction):
        """
        v13.0: Esegue un ordine DCA Intelligente.
        Converte la decisione DCA nel formato action e la passa al pipeline di esecuzione.
        """
        symbol = dca_action.symbol
        side = dca_action.action  # BUY o SELL
        eur_amount = dca_action.eur_amount

        logger.info(
            f"DCA EXECUTE: {side} {symbol} | EUR: {eur_amount:.2f} | "
            f"Tattica: {dca_action.tactical_command} (Confidence: {dca_action.confidence:.2f}) | "
            f"Reason: {dca_action.reason}"
        )

        if side == "BUY":
            action = {
                "symbol": symbol,
                "action": "BUY",
                "usdt_amount": eur_amount,  # In EUR per le coppie EUR
                "level_index": None  # DCA non usa livelli di griglia
            }
            await self._execute_apex_order(action)

        elif side == "SELL":
            # Per il SELL recupera la quantità dalla posizione DCA
            pos = self.dca_engine.positions.get(symbol)
            if pos and pos.total_qty > 0:
                sell_qty = pos.total_qty * 0.3  # Vendi il 30% (take profit parziale)
                action = {
                    "symbol": symbol,
                    "action": "SELL",
                    "quantity": sell_qty,
                    "level_index": None
                }
                await self._execute_apex_order(action)
            else:
                logger.warning(f"DCA SELL skipped: No position for {symbol}")

        # Registra in episodio per tracking
        self.episode_store.append_episode(
            "trading", "dca_decision",
            source="dca_engine",
            tags=[symbol, side, dca_action.tactical_command],
            payload={
                "symbol": symbol,
                "side": side,
                "eur_amount": eur_amount,
                "tactical_command": dca_action.tactical_command,
                "confidence": dca_action.confidence,
                "reason": dca_action.reason
            }
        )

    def _handle_rejection(self, decision, mode="NO_TRADE"):
        """Gestisce il rifiuto di un'opportunita e lo logga in EpisodeStore."""
        if not decision.candidate:
            return
        self.risk_tracker.emit_counterfactual_lesson(None, decision)
        import time
        record = {
            "symbol": decision.candidate.symbol,
            "side": decision.candidate.side,
            "timestamp": time.time(),
            "entry_price": decision.candidate.entry_price,
            "expected_edge_pct": decision.candidate.expected_edge_pct,
            "friction_total_pct": decision.friction.total_friction_pct if decision.friction else 0.0,
            "rejection_reason": decision.reason_codes[0] if decision.reason_codes else "unknown",
            "threshold_used": self.arbiter.min_net_edge_required,
            "rejection_mode": mode,
        }
        self.episode_store.append_episode("trading", "rejected_opportunity", record)

    def _maybe_evaluate_past_rejections(self):
        """Valuta gli esiti delle reiezioni a T+60m per l'apprendimento."""
        self.rejection_review_counter += 1
        if self.rejection_review_counter < 5:
            return
        self.rejection_review_counter = 0
        import time
        episodes = self.episode_store.load_episodes("trading", limit=20)
        pending = [e for e in episodes if e.get("kind") == "rejected_opportunity"]
        now = time.time()
        for ep in pending:
            payload = ep.get("payload", {})
            age = now - payload.get("timestamp", 0)
            if 3600 <= age <= 7200:
                symbol = payload.get("symbol")
                ticker = self.adapter.get_ticker_price(symbol)
                current_price = ticker.get("price", 0.0)
                if current_price > 0:
                    outcome = self.outcome_evaluator.evaluate_rejection(
                        StructuredRejectedTrade(**payload), current_price, now
                    )
                    self.lesson_store.append_lesson(
                        category="trading",
                        title=f"OUTCOME: {symbol} REJECTION REVIEW",
                        content=f"Rejection was {'CORRECT' if outcome.is_correct_rejection else 'TOO_CONSERVATIVE'}. "
                                f"Hypo Net: {outcome.hypothetical_net_return_pct:.4f}",
                    )

    async def _execute_apex_order(self, action):
        """Esecuzione market con protezione deterministica Iron Core v12.0 e Risk Kernel."""
        symbol = action["symbol"]
        side = action["action"]
        raw_qty = action.get("usdt_amount") if side == "BUY" else action.get("quantity")
        
        # 1. RISK KERNEL BARRIER (FASE 2 - Sovranit del Rischio)
        # Costruzione Intento per il Tribunale Supremo
        from ai_trader.risk.policy_models import TradeIntent, PortfolioState, SystemState
        import time

        # v12.1: Usa il risk_kernel già inizializzato nel boot (con policy corretta)
        risk_kernel = self.risk_kernel
        
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
                        if action.get("level_index") is not None:
                            self.grid_engine.record_buy(symbol, action["level_index"], avg_price, executed_qty)
                        # v13.0: Registra anche nel DCA Engine
                        self.dca_engine.record_buy(symbol, executed_qty, avg_price, exec_qty)
                    else:
                        if action.get("level_index") is not None:
                            self.grid_engine.record_sell(symbol, action["level_index"], avg_price, executed_qty)
                        self.dca_engine.record_sell(symbol, executed_qty, avg_price, executed_qty * avg_price)
                    logger.info(f"APEX ORDER SUCCESS: {symbol} {side} Filled: {executed_qty} @ {avg_price}")
                else:
                    self.risk_tracker.record_order_failure("zero_fill")
                    # Persistenza Incidente su Errori Ripetuti
                    if self.risk_tracker.consecutive_errors >= 3:
                        self.risk_tracker.emit_incident_lesson("Continuous Zero Fill", "EXCHANGE_FAILURE", "critical")
                    logger.error(f"APEX RECONCILIATION FAILURE: {symbol} Fill nullo. Status: {order.get('status')}")
            else:
                self.risk_tracker.record_order_failure("rejected")
                if self.risk_tracker.consecutive_errors >= 3:
                    self.risk_tracker.emit_incident_lesson("Repeated Rejection", "REJECTION_STREAK", "warning")
                logger.error(f"APEX EXECUTION REJECTED: {symbol} Error: {order.get('error')}")
                
        except Exception as e:
            self.risk_tracker.record_order_failure("crash")
            self.risk_tracker.emit_incident_lesson(f"Reactor Crash: {symbol}", "CRITICAL_CRASH", "critical")
            logger.error(f"APEX CRITICAL CRASH: Order {symbol}", error=str(e))

    async def run(self):
        """Reattore principale con NightSession safety wrapper."""
        # v12.5: NightSession override for overnight mode (Optional now)
        if self.night_mode:
            night_config = NightSessionConfig(
                allowed_symbols=self.target_symbols,
                max_open_positions=self.max_positions
            )
            self.night_session = NightSession(config=night_config)
            self.settings.WHITELIST_PAIRS = night_config.allowed_symbols
            logger.info(f"v12.5 NightSession ACTIVE: Whitelist={self.settings.WHITELIST_PAIRS}, MaxTrades={night_config.max_session_trades}")
        else:
            logger.info(f"FULL APEX ACTIVE: NightSession disabled. Whitelist={self.target_symbols}")
            self.settings.WHITELIST_PAIRS = self.target_symbols

        await self.boot_sequence()

        cycle_count = 0
        cycle_failures = 0
        while self.running:
            # Night Session hard stop -> generate report and exit
            if self.night_session and self.night_session.is_halted:
                logger.warning(f"NightSession HALT detected: {self.night_session.halt_reason}. Generating morning report.")
                report = self.night_session.generate_morning_report()
                print(f"\n=== MORNING REPORT ===")
                print(f"Trades: {report['trades_executed']} | PnL: {report['session_pnl']:.4f} | Halt: {report['halt_reason']}")
                break

            cycle_count += 1
            print(f"\n[APEX CYCLE #{cycle_count}] --- {datetime.now().strftime('%H:%M:%S')}")

            # 1. Check Salute Paladin (v11.0 priority)
            try:
                health = self.paladin.check_portfolio_health()
                print(f"I  Paladin: Status={health['status']} | Equity={health.get('equity', 0):.2f} | DD={health.get('drawdown', 0):.2f}%")
            except Exception as e:
                print(f"I  Paladin: Error={e}")

            # 2. Processo strategico (protected)
            try:
                await self.process_cycle()
                cycle_failures = 0  # reset on success
            except Exception as e:
                cycle_failures += 1
                logger.error(f"process_cycle CRASH #{cycle_failures}: {e}", error=str(e), trace=traceback.format_exc())
                print(f"[ERROR] Cycle #{cycle_count} failed ({cycle_failures}/3): {e}")
                if cycle_failures >= 3:
                    logger.error("3 consecutive cycle failures — halting session")
                    if self.night_session:
                        self.night_session._halt("CONSECUTIVE_CYCLE_FAILURES")
                        continue
                    else:
                        break

            # 3. AI Heartbeat (Ogni 10 cicli, solo se Ollama disponibile)
            if self.ollama_available and cycle_count % 10 == 0:
                try:
                    self.ollama.chat([{"role": "user", "content": "keepalive"}], max_tokens=1)
                except Exception:
                    pass

            await asyncio.sleep(self.interval)

        # Clean shutdown: always generate morning report
        if self.night_session:
            self.night_session.generate_morning_report()
        await self.shutdown_sequence()

async def main_async():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="live")
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--symbols", default="BTCUSDT")
    parser.add_argument("--max_positions", type=int, default=1)
    parser.add_argument("--night_mode", action="store_true", help="Abilita il constraint NightSession a 8 ore")
    args = parser.parse_args()
    
    symbol_list = [s.strip() for s in args.symbols.split(",")]
    
    reactor = ApexReactor(
        mode=args.mode,
        interval=args.interval,
        target_symbols=symbol_list,
        max_positions=args.max_positions,
        night_mode=args.night_mode
    )
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
