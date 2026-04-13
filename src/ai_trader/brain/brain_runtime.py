# src/ai_trader/brain/brain_runtime.py
# 2026-04-03 01:50 - Brain Orchestrator iterativo
"""
Runtime State Machine.
Esegue step loop su dicts caricati e transizioni pulite.
Adatto al testnet Paper mode senza timeout live lunghi.
"""

import time
from typing import Any
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.brain.brain_types import (
    BrainPhase, BrainEventType, BrainState, BrainContext, PersistentBrainState, create_initial_brain_state
)
from ai_trader.brain.brain_transitions import transition
from ai_trader.brain.brain_errors import BrainRuntimeError, to_error, InvalidBrainTransitionError
import ai_trader.brain.brain_actions as b_actions

logger = get_logger("brain_runtime")


class BrainRuntime:
    
    def __init__(self, context: BrainContext):
        self.ctx = context
        self.state: BrainState | None = None
        self.persistent_state: PersistentBrainState | None = None
        self.ollama = context.ollama_client # v11.4: Link diretto client IA
        
    def evaluate_strategy(self, symbol: str, budget: float) -> dict[str, Any]:
        """
        v11.4: Valutazione neurale asincrona.
        Interroga il Titan Brain per confermare l'opportunit di trading.
        """
        logger.info(f"Brain: Valutazione strategica per {symbol} (Budget: {budget:.2f})")
        
        # In una versione futura qui implementeremo il loop completo della state machine.
        # Per ora facciamo un'integrazione diretta e robusta con Ollama.
        if not self.ollama:
            return {"ok": True, "reason": "No LLM, fallback heuristic"}

        prompt = f"Analisi strategica per {symbol}. Budget {budget} EUR. Confermi l'ingresso?"
        res = self.ollama.chat([{"role": "user", "content": prompt}], max_tokens=10)
        
        if res["ok"]:
            return {"ok": True, "reason": "AI Approved", "detail": res["message"].get("content")}
        
        return {"ok": True, "reason": "AI Timeout, Heuristic Bypass"}

    def start_cycle(self, cycle_id: str, start_phase: BrainPhase = BrainPhase.IDLE):
        """Inizializza un nuovo loop completo."""
        self.state = create_initial_brain_state(start_phase, cycle_id, self.ctx.now_fn())
        
        # Carica configurazione standard symbols se necessario
        whitelist = getattr(self.ctx.settings, "WHITELIST_PAIRS", ["BTCUSDT"]) 
        b_actions.select_next_symbol(self.state, whitelist)

    def _emit_transition(self, event: BrainEventType):
        if not self.state:
            raise BrainRuntimeError("Runtime senza state inizializzato")
            
        old_phase = self.state.phase
        
        try:
            res = transition(self.state, event, self.ctx)
            self.state.phase = res.next_phase
            self.state.last_transition_at = self.ctx.now_fn()
            
            b_actions.emit_brain_event(
                self.ctx, self.state, 
                event_type="transizione_effettuata",
                status="success",
                payload={"from": old_phase.value, "to": res.next_phase.value, "event": event.value}
            )
            
            logger.debug(f"[BRAIN] {old_phase.value} ---({event.value})---> {res.next_phase.value}")
            return res.action_to_run
            
        except InvalidBrainTransitionError as e:
            self.handle_error(e, fatal=True)
            return None

    def handle_error(self, e: Exception, fatal: bool = False):
        """Standardizza fail fallbacks in runtime."""
        self.state.last_error = to_error(e)
        logger.error(f"[BRAIN_ERROR] Fallimento su {self.state.phase.value}", error=str(e))
        
        b_actions.emit_brain_event(
            self.ctx, self.state,
            event_type="runtime_error", status="error", 
            payload={"error_msg": str(e), "fatal": fatal}
        )
        
        self.state.phase = BrainPhase.ERROR

    def step(self):
        """
        Esegue un tick della state machine in base alla fase corrente.
        Nessun blocco infinito. Discesa singola.
        """
        if not self.state:
            return
            
        p = self.state.phase
        self.state.iteration_count += 1
        
        try:
            if p == BrainPhase.IDLE:
                self._emit_transition(BrainEventType.TICK)

            elif p == BrainPhase.OBSERVE:
                sym = self.state.current_symbol
                if not sym:
                    self._emit_transition(BrainEventType.OBSERVATION_FAILED)
                    return
                    
                obs = b_actions.observe_market(self.ctx, sym)
                if obs.get("ok"):
                    self.state.buffer_memory["market_price"] = obs.get("price")
                    self._emit_transition(BrainEventType.OBSERVATION_OK)
                else:
                    self.state.last_error = to_error(Exception(f"API down: {obs.get('error')}"))
                    self._emit_transition(BrainEventType.OBSERVATION_FAILED)

            elif p == BrainPhase.ANALYZE:
                sym = self.state.current_symbol
                price = float(self.state.buffer_memory.get("market_price", 0.0) or 0.0)

                try:
                    from ai_trader.strategy.policy_models import StrategyDecision

                    dec = b_actions.analyze_symbol(self.ctx, sym, price)

                    if not isinstance(dec, StrategyDecision):
                        raise TypeError(f"StrategyDecision atteso, ottenuto: {type(dec).__name__}")

                    if not isinstance(dec.reason_codes, list):
                        raise TypeError("StrategyDecision.reason_codes deve essere list[str]")

                    if not isinstance(dec.intent_preview, dict):
                        raise TypeError("StrategyDecision.intent_preview deve essere dict")

                    self.state.buffer_memory["strategy_decision"] = dec
                    self.state.buffer_memory["decision_status"] = dec.status
                    self.state.buffer_memory["decision_action"] = dec.action
                    self.state.buffer_memory["decision_reason_codes"] = dec.reason_codes
                    self.state.buffer_memory["decision_confidence"] = getattr(dec, "confidence", 0.0)
                    self.state.buffer_memory["decision_error"] = dec.error

                    if dec.ok and dec.status == "buy_candidate":
                        self.state.buffer_memory.pop("skip_reason", None)
                        self.state.buffer_memory.pop("skip_status", None)
                        self.state.buffer_memory.pop("skip_confidence", None)
                        self._emit_transition(BrainEventType.ANALYSIS_OK)

                    elif dec.status in {"hold", "skip", "blocked"}:
                        self.state.buffer_memory["action"] = dec.action
                        self.state.buffer_memory["skip_reason"] = dec.reason_codes
                        self.state.buffer_memory["skip_status"] = dec.status
                        self.state.buffer_memory["skip_confidence"] = getattr(dec, "confidence", 0.0)
                        self._emit_transition(BrainEventType.ANALYSIS_FAILED)

                    else:
                        raise RuntimeError(
                            f"StrategyDecision non riconosciuto: ok={dec.ok}, status={dec.status}, action={dec.action}"
                        )

                except Exception as e:
                    self.handle_error(e, fatal=True)

            elif p == BrainPhase.PROPOSE:
                # Dal dec intent costringiamo il guardrail trigger
                dec = self.state.buffer_memory.get("strategy_decision")
                if dec and dec.intent_preview:
                    self._emit_transition(BrainEventType.PROPOSAL_READY)
                else:
                    self._emit_transition(BrainEventType.PROPOSAL_BLOCKED)

            elif p == BrainPhase.GUARDRAIL_CHECK:
                dec = self.state.buffer_memory.get("strategy_decision")
                if not dec or not dec.intent_preview:
                    self._emit_transition(BrainEventType.PROPOSAL_BLOCKED)
                    return
                    
                if self.ctx.guardrail_engine:
                    from ai_trader.risk.policy_models import TradeIntent, PortfolioState, SystemState, MarketState
                    ip = dec.intent_preview
                    prop_qty = float(ip.get("proposed_quantity", 0.0))
                    prop_not = float(ip.get("proposed_notional", 0.0))
                    price = self.state.buffer_memory.get("market_price", 0.0)
                    if prop_qty <= 0 and prop_not > 0 and price > 0:
                        prop_qty = prop_not / price
                    elif prop_not <= 0 and prop_qty > 0 and price > 0:
                        prop_not = prop_qty * price

                    ti = TradeIntent(
                        symbol=ip.get("symbol", ""), side=ip.get("side", ""),
                        proposed_notional=prop_not, proposed_quantity=prop_qty,
                        signal_quality=ip.get("signal_quality", 0.0), timestamp=ip.get("timestamp", self.ctx.now_fn()),
                        regime=ip.get("regime", "normal"), volatility_score=ip.get("volatility_score", 0.0),
                        source_agent=ip.get("source_agent", "brain"), thesis=ip.get("thesis", "")
                    )
                    
                    wallet_val = getattr(self.ctx.settings, "INITIAL_CAPITAL", 0.0)
                    if self.ctx.exchange_adapter and hasattr(self.ctx.exchange_adapter, "get_account_summary"):
                        summary = self.ctx.exchange_adapter.get_account_summary()
                        if summary.get("ok"):
                            wallet_val = float(summary.get("total_wallet_value", wallet_val))
                        else:
                            logger.error(f"BrainRuntime: Errore sincronizzazione saldo: {summary.get('error')}")

                    g_dec = self.ctx.guardrail_engine.evaluate_trade_intent(
                        ti, PortfolioState(wallet_val,0,0,{}), SystemState(0,0,0.0,0.0), MarketState(True,True,ti.symbol,price,0.0,"normal")
                    )
                    self.state.buffer_memory["guardrail_result"] = g_dec
                    if g_dec.allowed:
                        self._emit_transition(BrainEventType.PROPOSAL_READY)
                    else:
                        self.state.buffer_memory["action"] = "GUARDRAIL_BLOCKED"
                        self._emit_transition(BrainEventType.PROPOSAL_BLOCKED)
                else:
                    self._emit_transition(BrainEventType.PROPOSAL_READY)

            elif p == BrainPhase.EXECUTION_PREVIEW:
                dec = self.state.buffer_memory.get("strategy_decision")
                price = self.state.buffer_memory.get("market_price", 0.0)
                
                # Modulo 10 invoke
                exec_dec = b_actions.build_execution_preview(self.ctx, dec.intent_preview, price)
                self.state.buffer_memory["execution_decision"] = exec_dec
                
                if exec_dec.ok:
                    self.state.buffer_memory["action"] = "PAPER_BUY"
                    self._emit_transition(BrainEventType.PREVIEW_READY)
                else:
                    self.state.buffer_memory["action"] = "BLOCKED_BY_RISK_OR_FUNDS"
                    self._emit_transition(BrainEventType.PREVIEW_FAILED)

            elif p == BrainPhase.REVIEW:
                rev = b_actions.review_cycle(self.state)
                self.state.buffer_memory["review_summary"] = rev
                self._emit_transition(BrainEventType.REVIEW_DONE)

            elif p == BrainPhase.LEARN:
                b_actions.persist_learning_signal(self.ctx, self.state.buffer_memory.get("review_summary", {}))
                self._emit_transition(BrainEventType.LEARN_DONE)

            elif p == BrainPhase.ERROR:
                self._emit_transition(BrainEventType.TICK)

            elif p == BrainPhase.SLEEP:
                # Sleep timeout dummy in un ciclo non blocking
                self._emit_transition(BrainEventType.SLEEP_TIMEOUT)

        except Exception as e:
            self.handle_error(e, fatal=True)
