# src/ai_trader/strategy/grid_engine.py
# 2026-04-12 - Grid Trading Engine
"""
GridEngine  Motore di Grid Trading per micro-profitti su mercati laterali.

Strategia:
- Piazza livelli di prezzo equidistanti tra un range basso e alto
- Quando il prezzo scende sotto un livello  ordine BUY
- Quando il prezzo sale sopra un livello (gi comprato)  ordine SELL
- Profitto = differenza tra livelli  quantit per livello

Ottimizzato per budget piccoli (50) su pairs come DOGE/USDT.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from datetime import datetime, timezone
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("grid_engine")


@dataclass
class GridLevel:
    """Singolo livello della griglia."""
    price: float
    index: int
    status: str = "empty"   # "empty" | "bought" | "pending_sell"
    buy_price: float = 0.0  # Prezzo effettivo di acquisto
    quantity: float = 0.0   # Quantit acquistata
    buy_order_id: str = ""
    sell_order_id: str = ""


@dataclass
class GridConfig:
    """Configurazione della griglia per un singolo pair."""
    symbol: str
    lower_price: float
    upper_price: float
    num_levels: int
    budget_usdt: float
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class GridState:
    """Stato completo della griglia per un pair."""
    config: GridConfig
    levels: list[GridLevel] = field(default_factory=list)
    total_invested: float = 0.0
    total_profit: float = 0.0
    total_trades: int = 0
    active: bool = True


class GridEngine:
    """
    Motore Grid Trading.
    Gestisce multipli pair con griglie indipendenti.
    Persiste lo stato su disco per sopravvivere ai restart.
    """

    def __init__(self, data_dir: Path | None = None):
        self.grids: dict[str, GridState] = {}
        self.data_dir = data_dir or Path("data/grids")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._load_state()
        logger.info("GridEngine inizializzato", grids_loaded=len(self.grids))

    def setup_grid(self, config: GridConfig) -> GridState:
        """
        Crea una nuova griglia per un pair.
        Calcola i livelli equidistanti tra lower e upper price.
        """
        sym = config.symbol
        step = (config.upper_price - config.lower_price) / config.num_levels

        levels = []
        for i in range(config.num_levels):
            price = config.lower_price + step * (i + 0.5)  # Centro del livello
            levels.append(GridLevel(price=round(price, 8), index=i))

        state = GridState(config=config, levels=levels)
        self.grids[sym] = state
        self._save_state()

        logger.info("Griglia creata",
            symbol=sym,
            levels=config.num_levels,
            range_low=config.lower_price,
            range_high=config.upper_price,
            budget=config.budget_usdt,
            step=round(step, 8)
        )
        return state

    def recalculate_adaptive_levels(self, symbol: str, current_price: float, atr: float, multiplier: float = 2.0):
        """
        Ricalcola i livelli della griglia basandosi sulla volatilit (ATR).
        I livelli comprati rimangono invariati per garantire il profitto,
        mentre i livelli vuoti vengono riposizionati.
        """
        if symbol not in self.grids:
            return

        grid = self.grids[symbol]
        num_levels = grid.config.num_levels
        
        # Calcolo nuovo range basato sull'ATR: Range = ATR * Multiplier
        # Lo step tra i livelli diventa proporzionale alla volatilit
        new_step = max(atr * multiplier / num_levels, current_price * 0.001) # Min step 0.1%
        
        new_lower = round(current_price - (new_step * (num_levels / 2)), 8)
        new_upper = round(current_price + (new_step * (num_levels / 2)), 8)
        
        # Aggiorna config
        grid.config.lower_price = new_lower
        grid.config.upper_price = new_upper
        
        # Riposizionamento livelli vuoti
        for i in range(num_levels):
            level = grid.levels[i]
            if level.status == "empty":
                # Nuovo prezzo teorico per questo indice
                new_price = new_lower + new_step * (i + 0.5)
                level.price = round(new_price, 8)
        
        self._save_state()
        logger.info(" Griglia Adattiva Ricalibrata", 
                    symbol=symbol, atr=round(atr, 8), 
                    new_range=f"{new_lower}-{new_upper}",
                    new_step=round(new_step, 8))

    def evaluate(self, symbol: str, current_price: float, min_profit_pct: float = 0.3) -> list[dict[str, Any]]:
        """
        Valuta la griglia dato il prezzo corrente e un target di profitto dinamico.
        
        Args:
            symbol: Pair da valutare
            current_price: Prezzo corrente del mercato
            min_profit_pct: Percentuale di profitto desiderata (default 0.3%)
        """
        if symbol not in self.grids:
            return []

        grid = self.grids[symbol]
        if not grid.active:
            return []

        actions = []
        budget_per_level = grid.config.budget_usdt / grid.config.num_levels

        for level in grid.levels:
            # BUY: prezzo corrente  sceso sotto il livello e il livello  vuoto
            if level.status == "empty" and current_price <= level.price:
                # Verifica che non abbiamo gi superato il budget
                remaining = grid.config.budget_usdt - grid.total_invested
                order_usdt = min(budget_per_level, remaining)

                if order_usdt >= 1.5:  # v10.50: Allineamento Dust Filter
                    actions.append({
                        "action": "BUY",
                        "symbol": symbol,
                        "level_index": level.index,
                        "level_price": level.price,
                        "current_price": current_price,
                        "usdt_amount": round(order_usdt, 2),
                        "estimated_qty": round(order_usdt / current_price, 8)
                    })

            # SELL: prezzo corrente  salito sopra il livello e il livello  comprato
            elif level.status == "bought" and current_price >= level.price:
                # Allineamento dinamico target profitto v10.50
                multiplier = 1.0 + (min_profit_pct / 100.0)
                min_sell_price = level.buy_price * multiplier

                if current_price >= min_sell_price:
                    actions.append({
                        "action": "SELL",
                        "symbol": symbol,
                        "level_index": level.index,
                        "level_price": level.price,
                        "buy_price": level.buy_price,
                        "current_price": current_price,
                        "quantity": level.quantity,
                        "estimated_profit_pct": round((current_price / level.buy_price - 1) * 100, 3)
                    })

        return actions

    def record_buy(self, symbol: str, level_index: int, price: float,
                   quantity: float, order_id: str = "") -> None:
        """Registra un acquisto eseguito."""
        if symbol not in self.grids:
            return

        grid = self.grids[symbol]
        for level in grid.levels:
            if level.index == level_index:
                level.status = "bought"
                level.buy_price = price
                level.quantity = quantity
                level.buy_order_id = order_id
                grid.total_invested += price * quantity
                grid.total_trades += 1
                break

        self._save_state()
        logger.info("BUY registrato", symbol=symbol, level=level_index, price=price, qty=quantity)

    def record_sell(self, symbol: str, level_index: int, price: float,
                    quantity: float, order_id: str = "") -> None:
        """Registra una vendita eseguita."""
        if symbol not in self.grids:
            return

        grid = self.grids[symbol]
        for level in grid.levels:
            if level.index == level_index:
                profit = (price - level.buy_price) * quantity
                grid.total_profit += profit
                grid.total_invested -= level.buy_price * level.quantity
                level.status = "empty"
                level.buy_price = 0.0
                level.quantity = 0.0
                level.sell_order_id = order_id
                grid.total_trades += 1
                
                # Auto-Compounding v10.50
                # Inietta il 50% del profitto nel budget della griglia stessa
                if profit > 0:
                    reinvestment = profit * 0.5
                    grid.config.budget_usdt += reinvestment
                    logger.info(f"Auto-Compounding: Reinvestito {reinvestment:.4f} nel budget di {symbol}")
                break

        self._save_state()
        logger.info("SELL registrato", symbol=symbol, level=level_index, price=price,
                     qty=quantity, profit=round(profit, 4))

    def get_status(self, symbol: str) -> dict[str, Any]:
        """Stato corrente della griglia per un pair."""
        if symbol not in self.grids:
            return {"ok": False, "error": f"No grid for {symbol}"}

        grid = self.grids[symbol]
        bought_levels = [l for l in grid.levels if l.status == "bought"]
        empty_levels = [l for l in grid.levels if l.status == "empty"]

        return {
            "ok": True,
            "symbol": symbol,
            "active": grid.active,
            "total_levels": len(grid.levels),
            "bought_levels": len(bought_levels),
            "empty_levels": len(empty_levels),
            "total_invested": round(grid.total_invested, 4),
            "total_profit": round(grid.total_profit, 4),
            "total_trades": grid.total_trades,
            "budget_remaining": round(grid.config.budget_usdt - grid.total_invested, 4),
            "range": f"{grid.config.lower_price} - {grid.config.upper_price}",
            "levels": [
                {"index": l.index, "price": l.price, "status": l.status,
                 "buy_price": l.buy_price, "qty": l.quantity}
                for l in grid.levels
            ]
        }

    def get_overall_status(self) -> dict[str, Any]:
        """Stato aggregato di tutte le griglie."""
        total_profit = sum(g.total_profit for g in self.grids.values())
        total_invested = sum(g.total_invested for g in self.grids.values())
        total_trades = sum(g.total_trades for g in self.grids.values())

        return {
            "active_grids": len([g for g in self.grids.values() if g.active]),
            "total_profit_usdt": round(total_profit, 4),
            "total_invested_usdt": round(total_invested, 4),
            "total_trades": total_trades,
            "grids": {sym: self.get_status(sym) for sym in self.grids}
        }

    # -------------------------------------------------------------------------
    # Persistenza state su disco
    # -------------------------------------------------------------------------

    def _save_state(self):
        """Salva lo stato di tutte le griglie su disco."""
        state_file = self.data_dir / "grid_state.json"
        data = {}
        for sym, grid in self.grids.items():
            data[sym] = {
                "config": {
                    "symbol": grid.config.symbol,
                    "lower_price": grid.config.lower_price,
                    "upper_price": grid.config.upper_price,
                    "num_levels": grid.config.num_levels,
                    "budget_usdt": grid.config.budget_usdt,
                    "created_at": grid.config.created_at
                },
                "levels": [
                    {"price": l.price, "index": l.index, "status": l.status,
                     "buy_price": l.buy_price, "quantity": l.quantity,
                     "buy_order_id": l.buy_order_id, "sell_order_id": l.sell_order_id}
                    for l in grid.levels
                ],
                "total_invested": grid.total_invested,
                "total_profit": grid.total_profit,
                "total_trades": grid.total_trades,
                "active": grid.active
            }

        state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load_state(self):
        """Carica lo stato precedente dal disco."""
        state_file = self.data_dir / "grid_state.json"
        if not state_file.exists():
            return

        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            for sym, gd in data.items():
                cfg = GridConfig(**gd["config"])
                levels = [GridLevel(**ld) for ld in gd["levels"]]
                self.grids[sym] = GridState(
                    config=cfg,
                    levels=levels,
                    total_invested=gd.get("total_invested", 0.0),
                    total_profit=gd.get("total_profit", 0.0),
                    total_trades=gd.get("total_trades", 0),
                    active=gd.get("active", True)
                )
            logger.info("Stato griglia caricato da disco", grids=len(self.grids))
        except Exception as e:
            logger.warning("Impossibile caricare stato griglia", error_msg=str(e))
