# src/ai_trader/risk/risk_state_tracker.py
# 2026-04-13 - Phase 3A: Risk State Tracker
"""
Gestore in-memory dello stato di rischio real-time.
Memorizza metriche di esposizione, pnl stimato e serie di errori/perdite.
"""

import time
import json
import re
from typing import Dict, Any, Optional
from ai_trader.risk.policy_models import PortfolioState, SystemState

class RiskStateTracker:
    """Tracking deterministico dello stato di rischio per il RiskKernel."""
    
    def __init__(self, lesson_store=None):
        # Session state
        self.session_start_time = time.time()
        self.session_start_balance = 0.0
        self.current_wallet_value = 0.0
        
        # Exposure
        self.current_total_exposure = 0.0
        self.per_symbol_exposure: Dict[str, float] = {}
        self.open_positions_count = 0
        
        # Performance/Health
        self.consecutive_losses = 0
        self.consecutive_errors = 0
        self.estimated_daily_drawdown_pct = 0.0
        self.estimated_weekly_drawdown_pct = 0.0
        self.session_pnl = 0.0
        
        # Cooldowns
        self.system_cooldown_until = None
        self.symbol_cooldowns: Dict[str, float] = {}
        
        # Persistence Bridge (v12.0)
        self.lesson_store = lesson_store
        
        # Audit
        self.last_risk_block_reason = None

    def attach_lesson_store(self, store):
        """Inietta il ponte di memoria persistente."""
        self.lesson_store = store

    def initialize_from_summary(self, summary: dict):
        """Sincronizzazione iniziale dall'account summary reale."""
        self.session_start_balance = summary.get("total_balance", 0.0)
        self.current_wallet_value = self.session_start_balance
        self.current_total_exposure = summary.get("total_exposure", 0.0)
        self.per_symbol_exposure = {} 
        self.open_positions_count = 0 

    def emit_incident_lesson(self, title: str, incident_type: str, severity: str = "warning"):
        """Emette una lezione strutturata (JSON-in-Markdown) verso Supermemory."""
        if not self.lesson_store:
            return

        now_ts = time.time()
        # Payload strutturato per il restore deterministico
        incident_data = {
            "version": "1.0",
            "incident_type": incident_type,
            "severity": severity,
            "occurred_at": now_ts,
            "consecutive_errors": self.consecutive_errors,
            "consecutive_losses": self.consecutive_losses,
            "daily_drawdown_pct": self.estimated_daily_drawdown_pct,
            "session_pnl_estimate": self.session_pnl,
            "system_cooldown_until": self.system_cooldown_until,
            "reason_codes": [self.last_risk_block_reason] if self.last_risk_block_reason else []
        }

        content = f"""## incident_payload
```json
{json.dumps(incident_data, indent=2)}
```

### Context
L'incidente di tipo **{incident_type}** è stato rilevato durante l'operatività del RiskKernel.
Serie errori: {self.consecutive_errors}
Cooldown fino a: {self.system_cooldown_until}
"""
        self.lesson_store.append_lesson(
            category="system",
            title=f"RISK_INCIDENT: {title}",
            content=content,
            tags=["risk_kernel", incident_type, severity]
        )

    def emit_counterfactual_lesson(self, decision: Any, arbiter_decision: Any):
        """
        Registra un'opportunit scartata (Counterfactual) per analisi futura.
        # Phase 6 Requirement
        """
        if not self.lesson_store or not arbiter_decision.candidate:
            return

        cand = arbiter_decision.candidate
        fric = arbiter_decision.friction
        
        counterfactual_data = {
            "version": "1.1",
            "event": "COUNTERFACTUAL_REJECTION",
            "symbol": cand.symbol,
            "side": cand.side,
            "gross_edge_pct": cand.expected_edge_pct,
            "net_edge_pct": arbiter_decision.net_edge_pct,
            "friction_total_pct": fric.total_friction_pct if fric else 0.0,
            "rejection_reasons": arbiter_decision.reason_codes,
            "quality": arbiter_decision.quality.value,
            "signal_strength": cand.signal_strength,
            "occurred_at": time.time()
        }

        content = f"""## counterfactual_payload
```json
{json.dumps(counterfactual_data, indent=2)}
```

### Rationale
Opportunita scartata su {cand.symbol} ({cand.side}).
Edge Netto: {arbiter_decision.net_edge_pct:.4f}
Motivi: {arbiter_decision.reason_codes}
"""
        self.lesson_store.append_lesson(
            category="trading",
            title=f"COUNTERFACTUAL: {cand.symbol} {cand.side} rejected",
            content=content,
            tags=["counterfactual", "rejection", cand.symbol]
        )

    def restore_recent_incident_state(self, lookback_seconds: int = 14400):
        """Ripristina lo stato (cooldown/errori) analizzando le ultime lezioni persistenti."""
        if not self.lesson_store:
            return

        lessons = self.lesson_store.read_lessons("system")
        if not lessons:
            return

        # Prendiamo l'ultima (ordinamento per filename YYYY-MM-DD-lesson-XXX)
        last_lesson_meta = lessons[-1]
        
        try:
            # Leggiamo il file reale dal path restituito dal meta
            from pathlib import Path
            content = Path(last_lesson_meta["path"]).read_text(encoding="utf-8")
            
            # Parsing blocco JSON strutturato
            match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if not match:
                # [NOT RECOVERABLE] - Dati non strutturati
                return

            data = json.loads(match.group(1))
            occurred_at = data.get("occurred_at", 0)
            
            # Verifichiamo se l'incidente  troppo vecchio (> 4 ore)
            if (time.time() - occurred_at) > lookback_seconds:
                return

            # Ripristino deterministico
            self.consecutive_errors = data.get("consecutive_errors", 0)
            self.consecutive_losses = data.get("consecutive_losses", 0)
            
            cooldown_until = data.get("system_cooldown_until")
            if cooldown_until and cooldown_until > time.time():
                self.system_cooldown_until = cooldown_until
                
            print(f"I  [RISK] Stato Ripristinato da Memoria Persistente (Incidente: {data['incident_type']})")
            
        except Exception:
            # [NOT RECOVERABLE] - Silenzioso per non bloccare il boot
            pass

    def record_order_fill(self, symbol: str, side: str, notional: float, qty: float):
        """Aggiorna lo stato dopo un fill confermato."""
        if side == "BUY":
            self.current_total_exposure += notional
            self.per_symbol_exposure[symbol] = self.per_symbol_exposure.get(symbol, 0.0) + notional
            # Nota: reset errori dopo fill positivo? 
            # Per ora teniamo le streak separate dagli ordini tecnici
        else: # SELL
            # Stima della riduzione esposizione
            self.current_total_exposure = max(0.0, self.current_total_exposure - notional)
            self.per_symbol_exposure[symbol] = max(0.0, self.per_symbol_exposure.get(symbol, 0.0) - notional)
            
        self.consecutive_errors = 0 # Ogni fill resetta la streak di errori tecnici

    def record_order_failure(self, error_type: str = "technical"):
        """Registra un fallimento tecnico o di rete."""
        self.consecutive_errors += 1

    def record_loss(self, amount: float):
        """Registra una perdita realizzata (pnl negativo)."""
        if amount < 0:
            self.consecutive_losses += 1
            self.session_pnl += amount
            self._update_drawdown()

    def record_gain(self, amount: float):
        """Registra un guadagno (resetta streak perdite)."""
        if amount > 0:
            self.consecutive_losses = 0
            self.session_pnl += amount
            self._update_drawdown()

    def record_risk_block(self, reason: str):
        """Registra un intervento del RiskKernel."""
        self.last_risk_block_reason = reason

    def _update_drawdown(self):
        """Calcola il drawdown stimato rispetto al balance iniziale."""
        if self.session_start_balance <= 0:
            return
        
        current_equity = self.session_start_balance + self.session_pnl
        if current_equity < self.session_start_balance:
            drawdown = (self.session_start_balance - current_equity) / self.session_start_balance
            self.estimated_daily_drawdown_pct = drawdown

    def get_portfolio_state(self) -> PortfolioState:
        """Genera snapshot per il RiskKernel."""
        return PortfolioState(
            wallet_value=self.current_wallet_value,
            current_total_exposure=self.current_total_exposure,
            open_positions_count=self.open_positions_count,
            per_symbol_exposure=self.per_symbol_exposure.copy()
        )

    def get_system_state(self) -> SystemState:
        """Genera snapshot per il RiskKernel."""
        return SystemState(
            consecutive_losses=self.consecutive_losses,
            consecutive_errors=self.consecutive_errors,
            daily_drawdown_pct=self.estimated_daily_drawdown_pct,
            weekly_drawdown_pct=self.estimated_weekly_drawdown_pct,
            session_pnl=self.session_pnl,
            system_cooldown_until=self.system_cooldown_until,
            symbol_cooldowns=self.symbol_cooldowns.copy(),
            last_risk_block_reason=self.last_risk_block_reason
        )
