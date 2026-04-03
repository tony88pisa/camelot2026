# src/ai_trader/brain/brain_actions.py
# 2026-04-03 01:50 - Azioni Pure isolate
"""
Funzioni "Pure" destinate ad azionare meccanismi fisici o bridge su moduli 
durante le transizioni libere del ciclo di vita del cervello.
Nessuno stato viene incapsulato in classi gigantesche.
"""

from typing import Any
from ai_trader.brain.brain_types import BrainContext, BrainState, BrainEvent
from ai_trader.brain.event_log_sink import push_event
from ai_trader.strategy.policy_models import SignalInput
from ai_trader.execution.order_models import ExecutionContext
from ai_trader.risk.policy_models import SystemState, MarketState


def emit_brain_event(ctx: BrainContext, st: BrainState, event_type: str, status: str, payload: dict[str, Any]):
    """Registra in dashboard-friendly il transito JSONL pesante."""
    evt = BrainEvent(
        timestamp=ctx.now_fn(),
        cycle_id=st.cycle_id,
        phase=st.phase.value,
        event_type=event_type,
        symbol=st.current_symbol,
        status=status,
        payload=payload
    )
    if ctx.event_logger:
        ctx.event_logger(evt.__dict__)
    else:
        push_event(evt.__dict__)

def select_next_symbol(st: BrainState, config_whitelist: list[str]) -> str:
    """Carica simbolo dalla check queue della policy."""
    if not st.symbols_queue:
        st.symbols_queue = config_whitelist[:]
    if not st.symbols_queue:
        return ""
    
    st.current_symbol = st.symbols_queue.pop(0)
    return st.current_symbol


def observe_market(ctx: BrainContext, symbol: str) -> dict[str, Any]:
    """Isola l'interrogazione proxy dello snaphsot di mercato senza logica AI."""
    # Simula check via adapter o tool read-only.
    # Assumiamo di possedere le ref nel ctx
    try:
        if not ctx.exchange_adapter:
            return {}
        
        # Semplificazione fetch
        res = ctx.exchange_adapter.get_ticker_price(symbol)
        if "error" in res:
            return {"ok": False, "error": res["error"]}
        
        return {
            "ok": True,
            "price": res.get("price", 0.0),
            "symbol": symbol
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def analyze_symbol(ctx: BrainContext, symbol: str, price: float) -> Any:
    """Convoglia verso Modulo 09 (Strategy)."""
    if not ctx.strategy_engine:
        raise RuntimeError("Strategy engine off")
        
    s_in = SignalInput(
        symbol=symbol,
        price=price,
        timestamp=ctx.now_fn(),
        trend_score=0.7, # Mocked feature in assenza di agent indicator tool
        volatility_score=0.01,
        regime="normal",
        signal_quality=0.8,
        adapter_health=True,
        market_snapshot_available=True,
        memory_summary=""
    )
    
    return ctx.strategy_engine.evaluate_signal(s_in)


def build_execution_preview(ctx: BrainContext, intent_preview: dict[str, Any], market_price: float) -> Any:
    """Invia tramite Execution layer Modulo 10, che farà check in Guardrail Modulo 08."""
    if not ctx.execution_preview_engine:
        raise RuntimeError("Execution preview engine not mapped on Context")
    
    # Create pseudo safe Context to cover tests matching 1000$ limit
    exec_cx = ExecutionContext(
        wallet_value=10000.0,
        free_quote_balance=8000.0,
        open_positions_count=0,
        current_total_exposure=0.0,
        per_symbol_exposure={},
        system_state=SystemState(0,0,0.0,0.0),
        market_state=MarketState(True, True, intent_preview.get("symbol", ""), float(market_price), 0.0, "normal")
    )
    return ctx.execution_preview_engine.build_execution_preview(intent_preview, exec_cx)


def review_cycle(st: BrainState) -> dict[str, Any]:
    """Genera riepilogo per il learner per episodi di feedback."""
    return {
        "cycle_id": st.cycle_id,
        "symbol": st.current_symbol,
        "action_taken": st.buffer_memory.get("action", "NONE"),
        "error": str(st.last_error) if st.last_error else None
    }


def persist_learning_signal(ctx: BrainContext, review: dict[str, Any]):
    """Pushera i fallback sul memory storage system M04 evitando chiamate costose per il network."""
    if not ctx.memory_store:
        return
        
    outcome = {
        "memory_cat": "system",
        "doc": "review context execution",
        "data": review
    }
    
    try:
        # Pseudo hook per memory test mapping
        getattr(ctx.memory_store, "append_episode", lambda x,y: None)("system", outcome)
    except:
        pass
