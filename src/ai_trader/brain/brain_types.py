# src/ai_trader/brain/brain_types.py
# 2026-04-03 01:50 - Core Types for Brain Runtime
"""
Types-as-Documentation: Rappresentazione dello stato dell'agente.
Ogni classe descrive tassativamente ci che il Brain pu e deve manipolare.
"""

from typing import Any, Callable
from dataclasses import dataclass, field
from enum import Enum


class BrainPhase(str, Enum):
    """Fasi deterministiche che costituiscono i nodi della State Machine."""
    IDLE = "IDLE"
    OBSERVE = "OBSERVE"
    ANALYZE = "ANALYZE"
    PROPOSE = "PROPOSE"
    GUARDRAIL_CHECK = "GUARDRAIL_CHECK"
    EXECUTION_PREVIEW = "EXECUTION_PREVIEW"
    REVIEW = "REVIEW"
    LEARN = "LEARN"
    SLEEP = "SLEEP"
    ERROR = "ERROR"


class BrainEventType(str, Enum):
    TICK = "tick"
    OBSERVATION_OK = "observation_ok"
    OBSERVATION_FAILED = "observation_failed"
    ANALYSIS_OK = "analysis_ok"
    ANALYSIS_FAILED = "analysis_failed"
    PROPOSAL_READY = "proposal_ready"
    PROPOSAL_BLOCKED = "proposal_blocked"
    PREVIEW_READY = "preview_ready"
    PREVIEW_FAILED = "preview_failed"
    REVIEW_DONE = "review_done"
    LEARN_DONE = "learn_done"
    SLEEP_TIMEOUT = "sleep_timeout"
    FATAL_ERROR = "fatal_error"


@dataclass
class BrainState:
    """Stato mutabile isolato al singolo thread di ciclo."""
    phase: BrainPhase
    cycle_id: str
    current_symbol: str
    symbols_queue: list[str]
    last_transition_at: str
    last_error: Exception | None = None
    iteration_count: int = 0
    buffer_memory: dict[str, Any] = field(default_factory=dict)


@dataclass
class PersistentBrainState:
    """Istantanea recuperabile e passata su disco/lesson."""
    last_decision: dict[str, Any] = field(default_factory=dict)
    last_guardrail_result: dict[str, Any] = field(default_factory=dict)
    last_execution_preview: dict[str, Any] = field(default_factory=dict)
    last_review_summary: str = ""
    last_lesson_ids: list[str] = field(default_factory=list)
    last_cycle_metrics: dict[str, Any] = field(default_factory=dict)
    last_successful_symbol: str = ""


@dataclass
class BrainContext:
    """Integrazione e dependencies di tipo Read-Only per le passate Action Pure."""
    settings: Any = None
    exchange_adapter: Any = None
    strategy_engine: Any = None
    guardrail_engine: Any = None
    execution_preview_engine: Any = None
    memory_store: Any = None
    logger: Any = None
    event_logger: Any = None
    clock: Any = None
    now_fn: Callable[[], str] = field(default_factory=lambda: (lambda: ""))
    mcp_orchestrator: Any = None
    ollama_client: Any = None # v11.4: Integrazione IA Titan Brain


@dataclass
class BrainEvent:
    """Event payload JSON-friendly da pushare nello Heavy Sink per Audit."""
    timestamp: str
    cycle_id: str
    phase: str
    event_type: str
    symbol: str
    status: str
    payload: dict[str, Any]


def create_initial_brain_state(start_phase: BrainPhase, cycle_id: str, now_ts: str) -> BrainState:
    """Factory per stato transitorio."""
    return BrainState(
        phase=start_phase,
        cycle_id=cycle_id,
        current_symbol="",
        symbols_queue=[],
        last_transition_at=now_ts,
        last_error=None,
        iteration_count=0
    )


def create_initial_persistent_brain_state() -> PersistentBrainState:
    """Factory per entry store."""
    return PersistentBrainState()
