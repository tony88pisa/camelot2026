# src/ai_trader/brain/__init__.py
# 2026-04-03 01:50 - Package exports aggregati
"""
Brain State Machine Runtime.
Architettura modellata sui pattern open source CLI per determinismo Agentico.
"""

from ai_trader.brain.brain_types import (
    BrainPhase, BrainEventType, BrainState, PersistentBrainState, BrainContext, BrainEvent
)
from ai_trader.brain.brain_errors import (
    BrainRuntimeError, BrainAbortError, MarketObservationError, InvalidBrainTransitionError
)
from ai_trader.brain.event_log_sink import initialize_event_log_sink, EventLogSink
from ai_trader.brain.brain_runtime import BrainRuntime

__all__ = [
    "BrainPhase",
    "BrainEventType",
    "BrainState",
    "PersistentBrainState",
    "BrainContext",
    "BrainEvent",
    "BrainRuntimeError",
    "BrainAbortError",
    "MarketObservationError",
    "InvalidBrainTransitionError",
    "initialize_event_log_sink",
    "EventLogSink",
    "BrainRuntime"
]
