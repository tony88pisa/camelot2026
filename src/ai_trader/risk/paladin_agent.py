# src/ai_trader/risk/paladin_agent.py
import time
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.exchange.binance_adapter import BinanceAdapter
from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.config.settings import get_settings

logger = get_logger("paladin_agent")

class PaladinAgent:
    """
    Agente Protettivo (Il Paladino).
    Vigila sulla salute globale del portafoglio e interviene in caso di flash crash.
    """

    def __init__(self, adapter: BinanceAdapter, episode_store: EpisodeStore = None):
        self.adapter = adapter
        self.episode_store = episode_store or EpisodeStore()
        self.settings = get_settings()
        
        # Stato interno
        self.max_equity = 0.0
        self.last_check_value = 0.0
        self.emergency_threshold_pct = 5.0 # 5% Drawdown = Codice Rosso
        self.is_emergency_active = False
        self.last_poll_time = 0.0
        self.poll_interval = 60.0 # v11.9.2: Controllo equity ogni 60s per risparmiare peso API

    def check_portfolio_health(self) -> dict:
        """Controlla se il portafoglio  in pericolo."""
        current_time = time.time()
        if current_time - self.last_poll_time < self.poll_interval and self.last_check_value > 0:
            return {"status": "OK", "equity": self.last_check_value, "drawdown": 0.0}
            
        self.last_poll_time = current_time
        logger.debug("Paladin: Check salute portafoglio (Deep API Sync)...")
        
        snapshot = self.adapter.get_account_snapshot()
        if "_error_internal" in snapshot:
            logger.error("Paladin: Impossibile ottenere snapshot account")
            return {"status": "ERROR"}

        balances = snapshot.get("balances", [])
        quote_asset = self.settings.QUOTE_CURRENCY
        total_value = 0.0
        
        # Calcolo valore totale istantaneo
        for b in balances:
            asset = b["asset"]
            free = float(b["free"])
            locked = float(b["locked"])
            total_qty = free + locked
            
            if total_qty == 0: continue
            
            if asset == quote_asset:
                total_value += free
            else:
                price_res = self.adapter.get_ticker_price(f"{asset}{quote_asset}")
                if price_res["ok"]:
                    total_value += total_qty * price_res["price"]
        
        # Logica High Water Mark (HWM)
        if total_value > self.max_equity:
            self.max_equity = total_value
            logger.info(f"Paladin: Nuovo Equity Peak raggiunto: {self.max_equity:.2f} {quote_asset}")
            
        # Calcolo Drawdown
        drawdown_pct = 0.0
        if self.max_equity > 0:
            drawdown_pct = ((self.max_equity - total_value) / self.max_equity) * 100
            
        self.last_check_value = total_value
        logger.info(f"Paladin Status: Equity={total_value:.2f} | Max={self.max_equity:.2f} | DD={drawdown_pct:.2f}%")
        
        # Verifica Urgenza
        if drawdown_pct >= self.emergency_threshold_pct and not self.is_emergency_active:
             self._trigger_emergency_protocol(total_value, drawdown_pct)
             return {"status": "EMERGENCY", "drawdown": drawdown_pct}
             
        return {"status": "OK", "equity": total_value, "drawdown": drawdown_pct}

    def _trigger_emergency_protocol(self, current_value: float, drawdown: float):
        """Attiva la liquidazione totale e ferma il sistema."""
        self.is_emergency_active = True
        msg = f"!!! PALADIN EMERGENCY ACTIVATED: Drawdown {drawdown:.2f}% !!!"
        logger.error(msg)
        
        # Registra il fallimento critico in memoria
        self.episode_store.append_episode(
            category="system",
            kind="paladin_emergency",
            payload={
                "drawdown_pct": drawdown,
                "equity_at_emergency": current_value,
                "max_equity": self.max_equity,
                "reason": "Sudden Portfolio Value Drop"
            },
            tags=["emergency", "paladin", "safety"]
        )
        
        # Esegue liquidazione reale
        res = self.adapter.emergency_liquidate_all(self.settings.QUOTE_CURRENCY)
        if res["ok"]:
            logger.warning("Paladin: Liquidazione d'emergenza completata con successo.")
        else:
            logger.critical(f"Paladin: ERRORE DURANTE LIQUIDAZIONE! {res.get('errors')}")

        # Segnalazione per il main loop
        with open("PALADIN_LOCK.txt", "w") as f:
            f.write(f"Emergency Triggered at {time.ctime()} due to {drawdown:.2f}% drawdown")
