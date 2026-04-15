# src/ai_trader/strategy/dca_engine.py
# 2026-04-14 - DCA Intelligent Engine: RAG-Powered Accumulation Strategy
"""
Motore DCA Intelligente potenziato dal Sentiment RAG.

Logica:
- BEARISH/FEAR  -> Compra aggressivo (accumula a sconto)
- NEUTRAL       -> Compra moderato (DCA standard)
- BULLISH/GREED -> NON compra, valuta vendita parziale (prendi profitto)

Il motore tiene traccia delle posizioni accumulate e del prezzo medio
di carico (Average Cost Basis) per ogni moneta.
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("dca_engine")

DCA_STATE_FILE = Path("data/dca/dca_state.json")


@dataclass
class DCAPosition:
    """Posizione accumulata tramite DCA per un singolo asset."""
    symbol: str
    total_qty: float = 0.0
    total_cost: float = 0.0  # In EUR
    avg_cost: float = 0.0
    num_buys: int = 0
    num_sells: int = 0
    realized_pnl: float = 0.0
    last_action: str = ""
    last_action_time: float = 0.0

    def record_buy(self, qty: float, price: float, cost_eur: float):
        """Registra un acquisto e aggiorna il prezzo medio."""
        self.total_qty += qty
        self.total_cost += cost_eur
        self.avg_cost = self.total_cost / self.total_qty if self.total_qty > 0 else 0.0
        self.num_buys += 1
        self.last_action = "BUY"
        self.last_action_time = time.time()

    def record_sell(self, qty: float, price: float, revenue_eur: float):
        """Registra una vendita parziale e calcola il PnL realizzato."""
        cost_of_sold = self.avg_cost * qty
        profit = revenue_eur - cost_of_sold
        self.realized_pnl += profit
        self.total_qty -= qty
        self.total_cost -= cost_of_sold
        if self.total_qty <= 0:
            self.total_qty = 0.0
            self.total_cost = 0.0
            self.avg_cost = 0.0
        self.num_sells += 1
        self.last_action = "SELL"
        self.last_action_time = time.time()
        return profit

    @property
    def unrealized_pnl(self):
        """Placeholder - calcolato esternamente col prezzo corrente."""
        return 0.0

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DCAAction:
    """Azione generata dal motore DCA."""
    symbol: str
    action: str           # "BUY", "SELL", "HOLD"
    eur_amount: float     # Quanto spendere/incassare in EUR
    reason: str           # Motivazione leggibile
    tactical_command: str # AGGRESSIVE_BUY, CAUTIOUS_BUY, HOLD, TAKE_PROFIT
    confidence: float     # 0.0 - 1.0


class DCAEngine:
    """
    DCA Intelligent Engine.
    
    Strategia:
    - Divide il budget in micro-tranche (es. 5-15€ per buy)
    - Compra PIÙ AGGRESSIVAMENTE quando il sentiment è FEAR/BEARISH
    - Compra NORMALMENTE quando NEUTRAL
    - NON compra quando GREED/BULLISH → valuta vendita parziale se in profitto
    - Cooldown tra acquisti per evitare overtrading
    """

    def __init__(self, base_tranche_eur: float = 12.0, cooldown_minutes: int = 30):
        self.base_tranche = base_tranche_eur
        self.cooldown_sec = cooldown_minutes * 60
        self.positions: dict[str, DCAPosition] = {}
        self._load_state()

    def _load_state(self):
        """Carica lo stato persistente delle posizioni DCA."""
        DCA_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if DCA_STATE_FILE.exists():
            try:
                with open(DCA_STATE_FILE, "r") as f:
                    data = json.load(f)
                for sym, pos_data in data.items():
                    self.positions[sym] = DCAPosition.from_dict(pos_data)
                logger.info(f"DCA State caricato: {len(self.positions)} posizioni")
            except Exception as e:
                logger.error(f"Errore caricamento DCA state: {e}")

    def _save_state(self):
        """Salva lo stato su disco."""
        try:
            DCA_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {sym: pos.to_dict() for sym, pos in self.positions.items()}
            with open(DCA_STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Errore salvataggio DCA state: {e}")

    def evaluate(self, symbol: str, current_price: float,
                 tactical_command: str,
                 free_balance_eur: float,
                 tp_pct: float = 5.0) -> DCAAction:
        """
        Valuta cosa fare per un dato simbolo in base al Comando Tattico (Caveman).
        
        Args:
            symbol: Coppia (es. BTCEUR)
            current_price: Prezzo corrente
            tactical_command: AGGRESSIVE_BUY / CAUTIOUS_BUY / HOLD / TAKE_PROFIT
            free_balance_eur: EUR disponibili nel wallet
            tp_pct: Take Profit percentuale per vendita parziale
            
        Returns:
            DCAAction con l'ordine suggerito
        """
        pos = self.positions.get(symbol, DCAPosition(symbol=symbol))

        # Cooldown check
        elapsed = time.time() - pos.last_action_time
        if elapsed < self.cooldown_sec and pos.last_action:
            return DCAAction(
                symbol=symbol, action="HOLD", eur_amount=0,
                reason=f"Cooldown attivo ({int(self.cooldown_sec - elapsed)}s rimanenti)",
                tactical_command=tactical_command,
                confidence=0.0
            )

        # === STRATEGIA DCA INTELLIGENTE (MoE GUIDED) ===

        # 1. AGGRESSIVE_BUY → Compra aggressivo (tranche maggiorata)
        if tactical_command == "AGGRESSIVE_BUY":
            multiplier = 1.5  # 50% in più della tranche base
            amount = min(self.base_tranche * multiplier, free_balance_eur * 0.4)
            amount = max(amount, 5.5)  # Floor: Binance Min Notional + margine
            if amount > free_balance_eur:  # Non superare il saldo
                return DCAAction(
                    symbol=symbol, action="HOLD", eur_amount=0,
                    reason="Saldo insufficiente per AGGRESSIVE_BUY",
                    tactical_command=tactical_command,
                    confidence=0.0
                )
            return DCAAction(
                symbol=symbol, action="BUY", eur_amount=round(amount, 2),
                reason="Tattica: Accumulo aggressivo (Whale/Fear confermato)",
                tactical_command=tactical_command,
                confidence=0.85
            )

        # 2. CAUTIOUS_BUY → Compra standard (tranche base)
        elif tactical_command == "CAUTIOUS_BUY":
            amount = min(self.base_tranche, free_balance_eur * 0.35)
            amount = max(amount, 5.5)  # Floor: Binance Min Notional + margine
            if amount > free_balance_eur:
                return DCAAction(
                    symbol=symbol, action="HOLD", eur_amount=0,
                    reason="Saldo insufficiente per CAUTIOUS_BUY",
                    tactical_command=tactical_command,
                    confidence=0.0
                )
            return DCAAction(
                symbol=symbol, action="BUY", eur_amount=round(amount, 2),
                reason="Tattica: DCA Cauto standard",
                tactical_command=tactical_command,
                confidence=0.6
            )

        # 3. TAKE_PROFIT / HOLD → Non comprare. Valuta vendita se in profitto.
        else:
            if pos.total_qty > 0 and pos.avg_cost > 0:
                unrealized_pct = ((current_price - pos.avg_cost) / pos.avg_cost) * 100
                if unrealized_pct >= tp_pct or tactical_command == "TAKE_PROFIT":
                    # Il comando diretto TAKE_PROFIT abbassa la soglia, oppure usiamo TP standard
                    sell_qty = pos.total_qty * 0.3
                    sell_eur = sell_qty * current_price
                    return DCAAction(
                        symbol=symbol, action="SELL", eur_amount=round(sell_eur, 2),
                        reason=f"TAKE_PROFIT confermato (PnL: {unrealized_pct:.1f}%): Vendita parziale 30%",
                        tactical_command=tactical_command,
                        confidence=0.9
                    )
                else:
                    return DCAAction(
                        symbol=symbol, action="HOLD", eur_amount=0,
                        reason=f"In attesa del TP ({unrealized_pct:.1f}% < {tp_pct}%)",
                        tactical_command=tactical_command,
                        confidence=0.3
                    )
            else:
                return DCAAction(
                    symbol=symbol, action="HOLD", eur_amount=0,
                    reason="Nessuna posizione aperta, attendo pullback.",
                    tactical_command=tactical_command,
                    confidence=0.2
                )

    def record_buy(self, symbol: str, qty: float, price: float, cost_eur: float):
        """Registra un acquisto eseguito."""
        if symbol not in self.positions:
            self.positions[symbol] = DCAPosition(symbol=symbol)
        self.positions[symbol].record_buy(qty, price, cost_eur)
        self._save_state()
        logger.info(f"DCA BUY registrato", symbol=symbol, qty=qty, price=price,
                    avg_cost=self.positions[symbol].avg_cost,
                    total_buys=self.positions[symbol].num_buys)

    def record_sell(self, symbol: str, qty: float, price: float, revenue_eur: float):
        """Registra una vendita eseguita."""
        if symbol not in self.positions:
            return 0.0
        profit = self.positions[symbol].record_sell(qty, price, revenue_eur)
        self._save_state()
        logger.info(f"DCA SELL registrato", symbol=symbol, qty=qty, price=price,
                    profit=round(profit, 4),
                    total_pnl=round(self.positions[symbol].realized_pnl, 4))
        return profit

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Riassunto del portafoglio DCA."""
        total_invested = sum(p.total_cost for p in self.positions.values())
        total_pnl = sum(p.realized_pnl for p in self.positions.values())
        active = {s: p.to_dict() for s, p in self.positions.items() if p.total_qty > 0}
        return {
            "total_invested_eur": round(total_invested, 2),
            "total_realized_pnl": round(total_pnl, 4),
            "active_positions": len(active),
            "positions": active
        }
