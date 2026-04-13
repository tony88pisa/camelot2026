# src/ai_trader/brain/brain_transitions.py
# 2026-04-03 01:50 - Single Transition Source of Truth
"""
Il CUORE. Una tabella esplicita che dice dal quale stato al quale evento
passa l'agente. Tutte le route logiche della CLI sono racchiuse in questo statement.
L'azione specifica pu essere incatenata.
"""

from typing import Any
from dataclasses import dataclass
from ai_trader.brain.brain_types import BrainPhase, BrainEventType, BrainState, BrainContext
from ai_trader.brain.brain_errors import InvalidBrainTransitionError


@dataclass
class TransitionResult:
    next_phase: BrainPhase
    action_to_run: str | None = None
    emit_event_type: str = "transition"


def transition(state: BrainState, event: BrainEventType, ctx: BrainContext) -> TransitionResult:
    """Mappa pura di transizione."""
    
    p = state.phase
    
    # IDLE states
    if p == BrainPhase.IDLE:
        if event == BrainEventType.TICK:
            return TransitionResult(BrainPhase.OBSERVE, "select_next_symbol")
            
    # OBSERVE states
    elif p == BrainPhase.OBSERVE:
        if event == BrainEventType.OBSERVATION_OK:
            return TransitionResult(BrainPhase.ANALYZE, "analyze_symbol")
        if event == BrainEventType.OBSERVATION_FAILED:
            return TransitionResult(BrainPhase.ERROR)
            
    # ANALYZE states
    elif p == BrainPhase.ANALYZE:
        if event == BrainEventType.ANALYSIS_OK:
            return TransitionResult(BrainPhase.PROPOSE, "build_intent_preview")
        if event == BrainEventType.ANALYSIS_FAILED:
            return TransitionResult(BrainPhase.REVIEW)
            
    # PROPOSE states
    elif p == BrainPhase.PROPOSE:
        if event == BrainEventType.PROPOSAL_READY:
            return TransitionResult(BrainPhase.GUARDRAIL_CHECK, "run_guardrail_check")
        if event == BrainEventType.PROPOSAL_BLOCKED:
            return TransitionResult(BrainPhase.REVIEW)
            
    # GUARDRAIL states (Logical, currently encapsulated often by EXEC PREVIEW in Module 10 so we bridge it)
    elif p == BrainPhase.GUARDRAIL_CHECK:
        if event == BrainEventType.PROPOSAL_READY:
            return TransitionResult(BrainPhase.EXECUTION_PREVIEW, "build_execution_preview")
        if event == BrainEventType.PROPOSAL_BLOCKED:
            return TransitionResult(BrainPhase.REVIEW)
            
    # EXECUTION PREVIEW states
    elif p == BrainPhase.EXECUTION_PREVIEW:
        if event == BrainEventType.PREVIEW_READY:
            return TransitionResult(BrainPhase.REVIEW)
        if event == BrainEventType.PREVIEW_FAILED:
            return TransitionResult(BrainPhase.REVIEW)
            
    # REVIEW & LEARN states
    elif p == BrainPhase.REVIEW:
        if event == BrainEventType.REVIEW_DONE:
            return TransitionResult(BrainPhase.LEARN, "persist_learning_signal")
            
    elif p == BrainPhase.LEARN:
        if event == BrainEventType.LEARN_DONE:
            return TransitionResult(BrainPhase.SLEEP)
            
    # ERROR and SLEEP boundaries
    elif p == BrainPhase.ERROR:
        if event == BrainEventType.TICK:
            return TransitionResult(BrainPhase.SLEEP)
            
    elif p == BrainPhase.SLEEP:
        if event == BrainEventType.SLEEP_TIMEOUT:
            return TransitionResult(BrainPhase.IDLE)
            
    raise InvalidBrainTransitionError(f"Transizione inaspettata nel cervello: Phase {p} -> Event {event}")
