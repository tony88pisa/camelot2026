from typing import Any
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.brain.brain_types import BrainContext, BrainState, BrainEvent
from ai_trader.brain.event_log_sink import push_event
from ai_trader.strategy.policy_models import SignalInput
from ai_trader.execution.order_models import ExecutionContext
from ai_trader.risk.policy_models import SystemState, MarketState

logger = get_logger("brain_actions")


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
    """Convoglia verso Modulo 09 (Strategy) usando dati reali dal MarketAnalyzer."""
    if not ctx.strategy_engine:
        raise RuntimeError("Strategy engine off")
    
    # Inizializza MarketAnalyzer se necessario (o usalo se presente nel contesto)
    from ai_trader.analysis.market_analyzer import MarketAnalyzer
    analyzer = MarketAnalyzer(exchange_adapter=ctx.exchange_adapter)
    
    # Esegue analisi tecnica reale
    analysis = analyzer.analyze(symbol)
    
    if not analysis.ok:
        # Fallback prudente se l'analisi fallisce
        logger.warning("Analisi tecnica fallita, uso fallback", symbol=symbol, error=analysis.error)
        trend_score = 0.0
        volatility_score = 0.05
        regime = "uncertain"
        signal_quality = 0.0
    else:
        trend_score = analysis.trend_score
        volatility_score = analysis.volatility_score
        regime = analysis.regime
        signal_quality = analysis.signal_quality
        
    s_in = SignalInput(
        symbol=symbol,
        price=price,
        timestamp=ctx.now_fn(),
        trend_score=trend_score,
        volatility_score=volatility_score,
        regime=regime,
        signal_quality=signal_quality,
        adapter_health=True,
        market_snapshot_available=True,
        memory_summary=analysis.recommendation if analysis.ok else "HOLD"
    )
    
    return ctx.strategy_engine.evaluate_signal(s_in)


def build_execution_preview(ctx: BrainContext, intent_preview: dict[str, Any], market_price: float) -> Any:
    """Invia tramite Execution layer Modulo 10, che far check in Guardrail Modulo 08."""
    if not ctx.execution_preview_engine:
        raise RuntimeError("Execution preview engine not mapped on Context")
    
    wallet_value = getattr(ctx.settings, "INITIAL_CAPITAL", 0.0)
    free_quote_balance = 0.0
    
    if ctx.exchange_adapter and hasattr(ctx.exchange_adapter, "get_account_summary"):
        summary = ctx.exchange_adapter.get_account_summary()
        if summary.get("ok"):
            wallet_value = summary.get("total_wallet_value", wallet_value)
            free_quote_balance = summary.get("free_quote_balance", free_quote_balance)
        else:
            logger.error(f"BrainActions: Errore recupero saldo reale: {summary.get('error')}. Uso fallback sicuro (0.0).")

    exec_cx = ExecutionContext(
        wallet_value=wallet_value,
        free_quote_balance=free_quote_balance,
        open_positions_count=0,
        current_total_exposure=0.0,
        per_symbol_exposure={},
        system_state=SystemState(0,0,0.0,0.0),
        market_state=MarketState(True, True, intent_preview.get("symbol", ""), float(market_price), 0.0, "normal")
    )
    return ctx.execution_preview_engine.build_execution_preview(intent_preview, exec_cx)


def consult_ai_decision(ctx: BrainContext, symbol: str, price: float, analysis_data: dict[str, Any]) -> dict[str, Any]:
    """
    Interroga Ollama (Gemma) per una validazione qualitativa.
    Ritorna la 'Thesis' e una raccomandazione pesata.
    """
    if not ctx.mcp_orchestrator:
        return {"ok": False, "thesis": "AI Brain disconnected", "recommendation": "HOLD"}
        
    prompt = f"""
    Sei un esperto Trader AI. Analizza i seguenti dati per {symbol} a prezzo {price}:
    - RSI(14): {analysis_data.get('rsi')}
    - Trend Score: {analysis_data.get('trend_score')} 
    - Regime: {analysis_data.get('regime')}
    - Signal Quality: {analysis_data.get('signal_quality')}
    
    Dovremmo procedere con l'acquisto? Fornisci una 'thesis' breve e decidi se BUY o HOLD.
    Rispondi in formato JSON: {{"thesis": "...", "recommendation": "BUY"|"HOLD"}}
    """
    
    try:
        # Usiamo l'orchestratore MCP per il loop di ragionamento
        res = ctx.mcp_orchestrator.run_cycle(prompt)
        
        # Estrazione grezza del JSON dalla risposta (semplificata)
        text = res.get("response", "").strip()
        if "BUY" in text.upper():
            rec = "BUY"
        else:
            rec = "HOLD"
            
        return {
            "ok": True,
            "thesis": text[:300], # Limitiamo la lunghezza
            "recommendation": rec
        }
    except Exception as e:
        logger.error("AI Consultation fallita", error=str(e))
        return {"ok": False, "thesis": f"AI Error: {str(e)}", "recommendation": "HOLD"}


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
