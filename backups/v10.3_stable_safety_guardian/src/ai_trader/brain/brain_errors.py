# src/ai_trader/brain/brain_errors.py
# 2026-04-03 01:50 - Core Error definitions
"""
Struttura gerarchica errori specifici per l'orchestratore del Bot.
Imita il pattern ad errori fortemente tipizzati per gestire la Failure Table.
"""

from typing import Any

class BrainRuntimeError(Exception):
    """Base exception class for Brain faults."""
    pass

class BrainAbortError(BrainRuntimeError):
    """Raised when runtime explicitly demands standard exit."""
    pass

class MarketObservationError(BrainRuntimeError):
    pass

class StrategyEvaluationError(BrainRuntimeError):
    pass

class GuardrailBlockedError(BrainRuntimeError):
    pass

class ExecutionPreviewError(BrainRuntimeError):
    pass

class MemoryLearningError(BrainRuntimeError):
    pass

class InvalidBrainTransitionError(BrainRuntimeError):
    """Fired se la state machine riceve un evento invalido in relazione ad un intent."""
    pass

# --- Helper Utilities ---

def to_error(e: Any) -> BrainRuntimeError:
    """Wrappa eccezioni terze limitando leaking."""
    if isinstance(e, BrainRuntimeError):
        return e
    return BrainRuntimeError(f"Unexpected Exception: {str(e)}")

def error_message(e: Exception) -> str:
    """Formatter testuale."""
    return f"[{e.__class__.__name__}] {str(e)}"

def short_error_stack(e: Exception, max_frames: int = 5) -> str:
    import traceback
    tb = traceback.format_exception(type(e), e, e.__traceback__)
    return "".join(tb[-max_frames:])

def is_abort_error(e: Exception) -> bool:
    return isinstance(e, BrainAbortError)
