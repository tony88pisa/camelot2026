# src/ai_trader/execution/position_tracker.py
# 2026-04-12 - Tracking delle posizioni aperte e P&L persistente
"""
PositionTracker  Gestisce l'inventario dei token acquistati e calcola il P&L.
Salva lo stato su disco in formato JSON per recuperare i dati al riavvio.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime, timezone
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("position_tracker")

@dataclass
class TradeRecord:
    symbol: str
    side: str  # "BUY" | "SELL"
    price: float
    quantity: float
    cost: float
    timestamp: str
    order_id: str = ""
    fee: float = 0.0
    thesis: str = ""

@dataclass
class Position:
    symbol: str
    avg_price: float
    total_quantity: float
    total_cost: float
    trades: list[TradeRecord] = field(default_factory=list)
    last_update: str = ""

    def __post_init__(self):
        if not self.last_update:
            self.last_update = datetime.now(timezone.utc).isoformat()

class PositionTracker:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir or Path("data/execution")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.positions: dict[str, Position] = {}
        self.history: list[TradeRecord] = []
        self._load_state()

    def add_trade(self, trade: TradeRecord):
        """Aggiunge un trade e aggiorna la posizione corrente."""
        self.history.append(trade)
        
        sym = trade.symbol
        if sym not in self.positions:
            self.positions[sym] = Position(symbol=sym, avg_price=0, total_quantity=0, total_cost=0)
        
        pos = self.positions[sym]
        
        if trade.side == "BUY":
            # Media ponderata del prezzo di carico
            new_total_qty = pos.total_quantity + trade.quantity
            new_total_cost = pos.total_cost + trade.cost
            pos.avg_price = new_total_cost / new_total_qty if new_total_qty > 0 else 0
            pos.total_quantity = new_total_qty
            pos.total_cost = new_total_cost
        elif trade.side == "SELL":
            # Riduzione posizione (FIFO semplificato)
            pos.total_quantity -= trade.quantity
            if pos.total_quantity <= 0:
                pos.total_quantity = 0
                pos.total_cost = 0
                pos.avg_price = 0
            else:
                pos.total_cost = pos.total_quantity * pos.avg_price
        
        pos.trades.append(trade)
        pos.last_update = datetime.now(timezone.utc).isoformat()
        self._save_state()
        
        logger.info("Trade registrato", symbol=sym, side=trade.side, price=trade.price, qty=trade.quantity)

    def get_position(self, symbol: str) -> Position | None:
        return self.positions.get(symbol)

    def get_all_positions(self) -> dict[str, Position]:
        return self.positions

    def _save_state(self):
        state_file = self.data_dir / "positions_state.json"
        data = {
            "positions": {
                sym: {
                    "symbol": p.symbol,
                    "avg_price": p.avg_price,
                    "total_quantity": p.total_quantity,
                    "total_cost": p.total_cost,
                    "last_update": p.last_update,
                    "trades": [vars(t) for t in p.trades]
                } for sym, p in self.positions.items()
            },
            "history": [vars(t) for t in self.history]
        }
        state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_state(self):
        state_file = self.data_dir / "positions_state.json"
        if not state_file.exists():
            return
        
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            for sym, pd in data.get("positions", {}).items():
                trades = [TradeRecord(**td) for td in pd.pop("trades", [])]
                self.positions[sym] = Position(**pd, trades=trades)
            self.history = [TradeRecord(**td) for td in data.get("history", [])]
            logger.info("Stato posizioni caricato", positions=len(self.positions), history=len(self.history))
        except Exception as e:
            logger.error("Errore caricamento stato posizioni", error_msg=str(e))
