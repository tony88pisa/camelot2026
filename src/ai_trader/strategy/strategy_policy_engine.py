# src/ai_trader/strategy/strategy_policy_engine.py
# 2026-04-03 01:25 - Engine Decisionale 
"""
Strategy Policy Engine Core. 
Non esegue ML inference. Esegue uno statement policy-driven che determina
l'action logica tra BUY, HOLD e SKIP basato sui metrics del mercato e portafoglio.
"""

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.strategy.policy_models import (
    StrategyPolicy,
    SignalInput,
    StrategyDecision,
    ReasonCode
)
from ai_trader.strategy.intent_preview import build_trade_intent_preview

logger = get_logger("strategy_engine")


class StrategyPolicyEngine:
    """Motore deterministico valutativo per policy inziali passive."""

    def __init__(self, policy: StrategyPolicy | None = None):
        self.policy = policy or StrategyPolicy()
        logger.info("StrategyPolicyEngine allocato")

    def _normalize_symbol(self, symbol: str) -> str:
        """Compatibilità stringa flatten"""
        return symbol.replace("/", "").replace("-", "").replace("_", "").upper()

    def evaluate_signal(self, signal_input: SignalInput) -> StrategyDecision:
        """
        Processa il segnale.
        Se tutte le constraint della policy passano, genera un intent BUY_CANDIDATE.
        Altrimenti retrocede a HOLD o SKIP compilando la thesis string.
        # 2026-04-03 01:25
        """
        logger.info("Valutazione Segnale", symbol=signal_input.symbol, sq=signal_input.signal_quality)
        
        norm_sym = self._normalize_symbol(signal_input.symbol)
        signal_input.normalized_symbol = norm_sym
        
        reasons = []
        action = "HOLD"
        status = "hold"
        thesis = "Neutral assessment."
        confidence = signal_input.signal_quality

        # --- GATES DI SICUREZZA INFRASTRUTTURALE ---
        
        if self.policy.require_adapter_health and not signal_input.adapter_health:
            reasons.append(ReasonCode.ADAPTER_UNAVAILABLE)
            
        if self.policy.require_market_snapshot and not signal_input.market_snapshot_available:
            reasons.append(ReasonCode.MARKET_SNAPSHOT_MISSING)
            
        if self.policy.require_memory_context and signal_input.memory_summary == "":
            reasons.append(ReasonCode.MEMORY_CONTEXT_MISSING)
            
        if norm_sym not in [self._normalize_symbol(s) for s in self.policy.allowed_symbols]:
            reasons.append(ReasonCode.SYMBOL_NOT_SUPPORTED)

        # Se ci sono bad adapter/missing data, skip immediately per salvaguardia totale.
        if len(reasons) > 0:
            return self._build_decision(
                norm_sym, "SKIP", "blocked", reasons, 0.0, 
                signal_input, f"SKIP: Parametri infrastrutturali mancanti: {reasons}"
            )

        # --- GATES STRATEGICI (Logica Analitica) ---

        if signal_input.regime in self.policy.blocked_regimes:
            reasons.append(ReasonCode.REGIME_BLOCKED)
            
        if signal_input.signal_quality < self.policy.min_signal_quality:
            reasons.append(ReasonCode.LOW_SIGNAL_QUALITY)
            
        if signal_input.trend_score < self.policy.min_trend_score:
            reasons.append(ReasonCode.LOW_TREND_SCORE)
            
        if signal_input.volatility_score > self.policy.max_volatility_score:
            reasons.append(ReasonCode.HIGH_VOLATILITY)

        if len(reasons) > 0:
            # Determinare se la motivazione è forte (SKIP) o debole (HOLD)
            if ReasonCode.HIGH_VOLATILITY in reasons or ReasonCode.REGIME_BLOCKED in reasons:
                action = "SKIP"
                status = "blocked"
                thesis = f"SKIP: {norm_sym} mercato instabile, regime o volatilità non consentiti dalla policy."
                confidence = 0.0
            else:
                action = "HOLD"
                status = "hold"
                thesis = f"HOLD: {norm_sym} metriche insufficienti per ingresso prudente ({[r.value for r in reasons]})."
                # Abbassa confidence in base al numero di limitazioni
                confidence = max(0.0, confidence - (0.2 * len(reasons)))
                
            return self._build_decision(norm_sym, action, status, reasons, confidence, signal_input, thesis)

        # --- CONDIZIONE FAVOREVOLE (BUY) ---
        
        # Aggiungo memory context override: Se c'era una memory ma con warnings massivi, possiamo declassare,
        # Ma al momento questo policy engine ignora il filtering NPL spinto per delegarlo ai Model Agents.
        action = "BUY"
        status = "buy_candidate"
        reasons.append(ReasonCode.BUY_CANDIDATE)
        thesis = f"BUY candidate: {norm_sym} in regime compatibile ({signal_input.regime}), trend elevato ({signal_input.trend_score}), volatilità controllata. Quality ok {signal_input.signal_quality}."
        
        return self._build_decision(norm_sym, action, status, reasons, confidence, signal_input, thesis)

    def _build_decision(self, norm_sym: str, action: str, status: str, reasons: list[ReasonCode], 
                        confidence: float, raw_signal: SignalInput, thesis: str) -> StrategyDecision:
        """Costruisce il payload emesso integrando il preview tool."""
        
        dec = StrategyDecision(
            ok=status != "blocked",
            status=status,
            action=action,
            normalized_symbol=norm_sym,
            signal_quality=raw_signal.signal_quality,
            trend_score=raw_signal.trend_score,
            volatility_score=raw_signal.volatility_score,
            confidence=confidence,
            reason_codes=[r.value for r in reasons],
            thesis=thesis,
            intent_preview={}
        )
        dec.intent_preview = build_trade_intent_preview(dec, raw_signal.price)
        return dec
