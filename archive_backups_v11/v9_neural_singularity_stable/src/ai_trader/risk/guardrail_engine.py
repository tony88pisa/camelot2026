# src/ai_trader/risk/guardrail_engine.py
# 2026-04-03 01:20 - Risk Guardrail Engine
"""
Motore deterministico principale. Valuta il TradeIntent contro 
i limit imposti rigidamente da RiskPolicy ed emette la GuardrailDecision.
"""

from datetime import datetime, timezone
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.risk.policy_models import (
    RiskPolicy,
    TradeIntent,
    GuardrailDecision,
    PortfolioState,
    SystemState,
    MarketState,
    ReasonCode
)

# 2026-04-03 01:20 - Logger per Audit Trail dei check risk
logger = get_logger("risk_guardrail")


class GuardrailEngine:
    """
    Rappresenta l'unico gateway autoritativo prima che una richiesta di trading 
    sia processata. Solo le transazioni APPROVED passano all'Execution Engine.
    # 2026-04-03 01:20
    """

    def __init__(self, policy: RiskPolicy | None = None):
        self.policy = policy or RiskPolicy()
        logger.info("GuardrailEngine allocato", policy_mode="testnet" if not self.policy.live_mode else "LIVE")

    def _normalize_symbol(self, symbol: str) -> str:
        """Compatibilit: formatta senza spazi o separatori (es. BTCUSDT)"""
        return symbol.replace("/", "").replace("-", "").replace("_", "").upper()

    def evaluate_trade_intent(
        self,
        intent: TradeIntent,
        portfolio_state: PortfolioState,
        system_state: SystemState,
        market_state: MarketState
    ) -> GuardrailDecision:
        """
        Struttura logica deterministica di check in sequenza, scartando su short circuit.
        # 2026-04-03 01:20
        """
        logger.info("Evaluazione Intent avviata", symbol=intent.symbol, side=intent.side, notional=intent.proposed_notional)
        
        reason_codes = []
        now = datetime.now(timezone.utc).timestamp()
        
        # Snapshot rapido per il payload di risposta
        snapshot = {
            "portfolio": portfolio_state.__dict__,
            "system": {
                "cooldown_until": system_state.system_cooldown_until,
                "consecutive_errors": system_state.consecutive_errors,
                "daily_dd": system_state.daily_drawdown_pct
            },
            "market_price": market_state.price
        }
        
        norm_sym = self._normalize_symbol(intent.symbol)

        # 1. Verifiche di integrit e salute adattatore e dati
        if self.policy.require_adapter_health and not market_state.adapter_health:
            reason_codes.append(ReasonCode.ADAPTER_UNHEALTHY)
            
        if not market_state.market_snapshot_available or market_state.price <= 0:
            reason_codes.append(ReasonCode.MARKET_DATA_MISSING)

        # 2. Hard limits: Mode & Size Validator
        if intent.proposed_quantity <= 0 or intent.proposed_notional <= 0:
            reason_codes.append(ReasonCode.INVALID_SIZE)
            
        if self.policy.allow_short is False and intent.side.lower() == "sell":
            # Per logiche spot, vendere non  short_selling se la merce  nel wallet.
            # Questo test sar pi rigoroso in integration con inventory checking.
            pass

        # 3. Whitelist / Symbol Checking
        if norm_sym not in [self._normalize_symbol(s) for s in self.policy.whitelist_pairs]:
            reason_codes.append(ReasonCode.SYMBOL_NOT_ALLOWED)
            
        if intent.regime == "forbidden":
            reason_codes.append(ReasonCode.SYMBOL_NOT_ALLOWED)

        # 4. Exposure & Open Limits
        if portfolio_state.open_positions_count >= self.policy.max_open_trades:
            reason_codes.append(ReasonCode.TOO_MANY_OPEN_TRADES)
            
        new_total_exp = (portfolio_state.current_total_exposure + intent.proposed_notional) / portfolio_state.wallet_value if portfolio_state.wallet_value > 0 else 0
        if new_total_exp > self.policy.max_total_exposure_pct:
            reason_codes.append(ReasonCode.TOTAL_EXPOSURE_LIMIT)
            
        new_single_exp = intent.proposed_notional / portfolio_state.wallet_value if portfolio_state.wallet_value > 0 else 0
        if new_single_exp > self.policy.max_single_position_pct:
            reason_codes.append(ReasonCode.SINGLE_POSITION_LIMIT)

        # 5. Fallimenti organici (Drawdown / Errori accumulati)
        if system_state.consecutive_errors >= self.policy.max_consecutive_errors:
            reason_codes.append(ReasonCode.TOO_MANY_CONSECUTIVE_ERRORS)
            
        if system_state.consecutive_losses >= self.policy.max_consecutive_losses:
            reason_codes.append(ReasonCode.TOO_MANY_CONSECUTIVE_LOSSES)
            
        if system_state.daily_drawdown_pct > self.policy.max_daily_drawdown_pct:
            reason_codes.append(ReasonCode.DAILY_DRAWDOWN_LIMIT)
            
        if system_state.weekly_drawdown_pct > self.policy.max_weekly_drawdown_pct:
            reason_codes.append(ReasonCode.WEEKLY_DRAWDOWN_LIMIT)

        # 6. Analisi Qualitativa (Volatilit e Signal Score)
        if intent.signal_quality < self.policy.min_signal_quality:
            reason_codes.append(ReasonCode.LOW_SIGNAL_QUALITY)
            
        if intent.volatility_score > self.policy.volatility_block_threshold:
            reason_codes.append(ReasonCode.HIGH_VOLATILITY)

        # 7. Cooldown / Temporizzazione
        if system_state.system_cooldown_until and now < system_state.system_cooldown_until:
            reason_codes.append(ReasonCode.SYSTEM_COOLDOWN_ACTIVE)
            
        sym_cooldown = system_state.symbol_cooldowns.get(norm_sym)
        if sym_cooldown and now < sym_cooldown:
            reason_codes.append(ReasonCode.SYMBOL_COOLDOWN_ACTIVE)

        decide_allow = len(reason_codes) == 0
        if decide_allow:
            reason_codes.append(ReasonCode.APPROVED)
            status = "approved"
        else:
            status = "blocked"

        out_decision = GuardrailDecision(
            ok=decide_allow,
            allowed=decide_allow,
            status=status,
            reason_codes=[r.value for r in reason_codes],
            normalized_symbol=norm_sym,
            approved_notional=intent.proposed_notional if decide_allow else 0.0,
            risk_snapshot=snapshot,
            error="Blocks exist" if not decide_allow else None
        )
        
        # Log Audit the transaction outcome
        logger.info("Guardrail Checked", 
            symbol=norm_sym, 
            allowed=decide_allow, 
            reasons=out_decision.reason_codes
        )
        
        return out_decision
