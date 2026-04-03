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
        
        try:
            res = transition(self.state, BrainEventType.OBSERVATION_FAILED, self.ctx)
            self.state.phase = res.next_phase
        except:
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
                price = self.state.buffer_memory.get("market_price", 0.0)
                
                # Modulo 09 (Strategy Evaluate Signal) proxy hook
                dec = b_actions.analyze_symbol(self.ctx, sym, price)
                self.state.buffer_memory["strategy_decision"] = dec
                
                if dec.ok and dec.status == "buy_candidate":
                    self._emit_transition(BrainEventType.ANALYSIS_OK)
                else:
                    # Hold o Skip
                    self.state.buffer_memory["action"] = dec.action
                    self._emit_transition(BrainEventType.ANALYSIS_FAILED)

            elif p == BrainPhase.PROPOSE:
                # Dal dec intent costringiamo il guardrail trigger
                dec = self.state.buffer_memory.get("strategy_decision")
                if dec and dec.intent_preview:
                    self._emit_transition(BrainEventType.PROPOSAL_READY)
                else:
                    self._emit_transition(BrainEventType.PROPOSAL_BLOCKED)

            elif p == BrainPhase.GUARDRAIL_CHECK:
                self._emit_transition(BrainEventType.PROPOSAL_READY) # Force check into EXEC

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

    def run_once(self):
        """Gira finchè non sbatte su uno state di requie come IDLE post Sleep."""
        limit = 20
        while limit > 0:
            p = self.state.phase
            if p == BrainPhase.IDLE and self.state.iteration_count > 0:
                break
                
            self.step()
            limit -= 1
            
    def run_forever(self, sleep_sec: float = 1.0):
        """Demone infinito."""
        while True:
            if not self.state or self.state.phase == BrainPhase.IDLE:
                from datetime import datetime
                self.start_cycle(f"CYC-{int(datetime.now().timestamp())}")
            self.step()
            time.sleep(sleep_sec)
