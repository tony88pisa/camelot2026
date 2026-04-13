# src/ai_trader/execution/execution_preview_engine.py
# 2026-04-03 01:35 - Execution Preview Engine
"""
Motore che converte TradeIntentPreviews strategiche validandole
sul Guardrail Engine formandone payload eseguibili 'Paper' senza touch API.
"""

from typing import Any
from datetime import datetime, timezone

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.risk.policy_models import TradeIntent, PortfolioState
from ai_trader.risk.guardrail_engine import GuardrailEngine
from ai_trader.execution.order_models import (
    PaperOrderRequest, 
    ExecutionPreviewDecision, 
    ExecutionContext, 
    ReasonCode
)

logger = get_logger("exec_preview")


class ExecutionPreviewEngine:
    """Implementa lo strato costruttivo dell'ordine e la logica di fallback wallet in pre-flight."""

    def __init__(self, guardrail_engine: GuardrailEngine | None = None):
        self.guardrail = guardrail_engine or GuardrailEngine()
        logger.info("ExecutionPreviewEngine online")

    def _intent_to_guardrail_intent(self, intent_dict: dict[str, Any]) -> TradeIntent | None:
        """Converte il dict payload del tool nello standard object."""
        try:
            return TradeIntent(
                symbol=intent_dict.get("symbol", ""),
                side=intent_dict.get("side", ""),
                proposed_notional=intent_dict.get("proposed_notional", 0.0),
                proposed_quantity=intent_dict.get("proposed_quantity", 0.0),
                signal_quality=intent_dict.get("signal_quality", 0.0),
                timestamp=intent_dict.get("timestamp", datetime.now(timezone.utc).isoformat()),
                regime=intent_dict.get("regime", "neutral"),
                volatility_score=intent_dict.get("volatility_score", 0.0),
                source_agent=intent_dict.get("source_agent", "unknown"),
                thesis=intent_dict.get("thesis", "")
            )
        except Exception as e:
            logger.error("Deserialization error per l'Intent del Guardrail", error_msg=str(e))
            return None

    def build_execution_preview(
        self, intent_preview: dict[str, Any], context: ExecutionContext
    ) -> ExecutionPreviewDecision:
        """
        Metodo centrale:
        1) Valida input
        2) Spedisce al Risk per safe verification
        3) Se OK, valuta coperture di funds sul Context ed estende quantit.
        # 2026-04-03 01:35
        """
        reason_codes = []
        
        # Iniziale checks null values o invalidi primitivi
        if not intent_preview:
            return self._build_fail_decision([ReasonCode.PREVIEW_INVALID_INPUT], "intent prediction empty")
            
        sym = intent_preview.get("symbol", "")
        if not sym:
            return self._build_fail_decision([ReasonCode.INVALID_SYMBOL], "Symbol string missing")
            
        if intent_preview.get("side", "").upper() != "BUY":
            return self._build_fail_decision([ReasonCode.INVALID_SIDE], "Only BUY allowed currently")
            
        # Ref Market checks
        ref_price = context.market_state.price
        if ref_price <= 0:
            return self._build_fail_decision([ReasonCode.MISSING_REFERENCE_PRICE], "Price reference = 0 on context market")

        # 3. Notional and Quantity fallbacks before evaluating with Guardrail
        prop_notional = float(intent_preview.get("proposed_notional", 0.0))
        prop_qty = float(intent_preview.get("proposed_quantity", 0.0))
        
        if prop_notional <= 0 and prop_qty <= 0:
            return self._build_fail_decision([ReasonCode.MISSING_NOTIONAL_AND_QUANTITY], "No size proposed")

        if prop_qty <= 0 and prop_notional > 0:
            prop_qty = prop_notional / ref_price
        
        if prop_notional <= 0 and prop_qty > 0:
            prop_notional = prop_qty * ref_price
            
        intent_preview["proposed_notional"] = prop_notional
        intent_preview["proposed_quantity"] = prop_qty

        # Conversione per il Guardrail
        gi = self._intent_to_guardrail_intent(intent_preview)
        if not gi:
            return self._build_fail_decision([ReasonCode.PREVIEW_INVALID_INPUT], "TradeIntent build issue")

        # Configurazione pseudo-wallet per lo State inviato al Guardrail (copiando i balances reali del preview)
        pf_state = PortfolioState(
            wallet_value=context.wallet_value,
            current_total_exposure=context.current_total_exposure,
            open_positions_count=context.open_positions_count,
            per_symbol_exposure=context.per_symbol_exposure
        )

        # 1. INVIO AL GUARDRAIL
        g_dec = self.guardrail.evaluate_trade_intent(
            gi, pf_state, context.system_state, context.market_state
        )

        # 2. Rejection Logic del Guardrail
        if not g_dec.allowed:
            logger.info("Guardrail Ha Bloccato il preview", symbol=sym, reasons=g_dec.reason_codes)
            return ExecutionPreviewDecision(
                ok=False,
                status="blocked",
                guardrail_allowed=False,
                reason_codes=[ReasonCode.PREVIEW_BLOCKED_BY_GUARDRAIL.value] + g_dec.reason_codes,
                paper_order={},
                risk_decision=g_dec.to_dict(),
                error="Blocked by Risk Engine"
            )

        # 3. Validazioni liquidit reali (Post Guardrail limit che non fa conto dei fondi Quote liquidi precisi)

        # Check fondi liquidi sul account context "free" limit (Wallet liquidity)
        if context.free_quote_balance < prop_notional:
            logger.warning("Fondi limitati al check finale", req=prop_notional, free=context.free_quote_balance)
            return ExecutionPreviewDecision(
                ok=False,
                status="invalid",
                guardrail_allowed=True, # Era ok per il risk! Ma i soldi veri son bassi
                reason_codes=[ReasonCode.INSUFFICIENT_WALLET.value],
                paper_order={},
                risk_decision=g_dec.to_dict(),
                error="Insufficient free quote balance for trade"
            )

        # Verifica polvere finale (se order cost nullo per errore float)
        if prop_qty < 0.0000001:
            return self._build_fail_decision([ReasonCode.INVALID_QUANTITY], "Quantity represents dust precision limit")

        # Mappatura e Conclusione PAPER Order Request
        order_req = PaperOrderRequest(
            symbol=gi.symbol,
            side="BUY",
            order_type="PAPER_MARKET",
            proposed_notional=round(prop_notional, 4),
            proposed_quantity=prop_qty,
            reference_price=ref_price,
            estimated_cost=round(prop_notional, 4),
            regime=gi.regime,
            signal_quality=gi.signal_quality,
            source_agent=gi.source_agent,
            thesis=gi.thesis,
            timestamp=datetime.now(timezone.utc).isoformat()
        )

        logger.info("Preview build approvato live", symbol=sym, quant=prop_qty, ext_cost=prop_notional)

        return ExecutionPreviewDecision(
            ok=True,
            status="approved_preview",
            guardrail_allowed=True,
            reason_codes=[ReasonCode.PREVIEW_APPROVED.value],
            paper_order=order_req.__dict__,
            risk_decision=g_dec.to_dict(),
            error=None
        )

    def _build_fail_decision(self, code_list: list[ReasonCode], err: str) -> ExecutionPreviewDecision:
        return ExecutionPreviewDecision(
            ok=False,
            status="invalid",
            guardrail_allowed=False,
            reason_codes=[c.value for c in code_list],
            paper_order={},
            risk_decision={},
            error=err
        )
