# src/ai_trader/exchange/binance_adapter.py
import hashlib
import hmac
import time
import requests
from urllib.parse import urlencode
from ai_trader.config.settings import get_settings
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.core.neural_patches import get_neural_override

logger = get_logger("binance_adapter")

class BinanceAdapter:
    """
    Adapter Universale per Binance (Spot).
    Supporta sia Mainnet (Live) che Testnet (Simulazione).
    Sincronizzato con logica di ordine v6.5.
    """

    def __init__(self, mode: str = "testnet"):
        settings = get_settings()
        self.mode = mode
        
        if mode == "mainnet":
            self.base_url = settings.BINANCE_MAINNET_BASE_URL.rstrip("/")
            self.api_key = settings.BINANCE_MAINNET_API_KEY
            self.api_secret = settings.BINANCE_MAINNET_API_SECRET
        else:
            self.base_url = settings.BINANCE_TESTNET_BASE_URL.rstrip("/")
            self.api_key = settings.BINANCE_TESTNET_API_KEY
            self.api_secret = settings.BINANCE_TESTNET_API_SECRET
            
        self.session = requests.Session()
        logger.info(f"BinanceAdapter inizializzato in modalit {mode}", base_url=self.base_url)

    def _has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _sign_payload(self, params: dict) -> str:
        if not self.api_secret: return ""
        query_string = urlencode({k: v for k, v in params.items() if k != "signature"})
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, endpoint: str, params: dict = None, private: bool = False) -> dict:
        params = params or {}
        headers = {}
        if private:
            if not self._has_credentials(): return {"_error_internal": "auth_missing"}
            headers["X-MBX-APIKEY"] = self.api_key
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = 5000
            params["signature"] = self._sign_payload(params)
        
        url = f"{self.base_url}{endpoint}"
        try:
            resp = self.session.request(method, url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200: return resp.json()
            err = resp.json().get("msg", resp.text) if resp.status_code != 404 else "Not Found"
            return {"_error_internal": f"HTTP {resp.status_code}: {err}"}
        except Exception as e:
            return {"_error_internal": str(e)}

    def get_server_time(self) -> dict:
        res = self._request("GET", "/api/v3/time")
        return {"ok": True, "server_time": res.get("serverTime"), "error": None} if "serverTime" in res else {"ok": False, "error": res}

    def health_check(self) -> dict:
        keys_setup = self._has_credentials()
        pub_check = self.get_server_time()
        pub_ok = pub_check["ok"]
        priv_ok = False
        if pub_ok and keys_setup:
            priv_check = self.get_account_snapshot()
            priv_ok = "_error_internal" not in priv_check
        
        return {
            "ok": pub_ok,
            "source": f"binance_{self.mode}",
            "api_keys_configured": keys_setup,
            "public_endpoints_available": pub_ok,
            "private_endpoints_available": priv_ok,
            "status": "ready" if priv_ok else "partial"
        }

    def get_ticker_price(self, symbol: str) -> dict:
        res = self._request("GET", "/api/v3/ticker/price", {"symbol": symbol})
        return {"ok": True, "price": float(res["price"]), "error": None} if "price" in res else {"ok": False, "error": res}

    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 50) -> list:
        res = self._request("GET", "/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})
        return res if isinstance(res, list) else []

    def get_24h_tickers(self) -> list:
        res = self._request("GET", "/api/v3/ticker/24hr")
        return res if isinstance(res, list) else []

    def get_account_snapshot(self) -> dict:
        return self._request("GET", "/api/v3/account", private=True)

    def get_symbol_info(self, symbol: str) -> dict:
        """Recupera informazioni sul simbolo inclusi i filtri (LOT_SIZE, ecc)."""
        res = self._request("GET", "/api/v3/exchangeInfo", {"symbol": symbol})
        if "symbols" in res and len(res["symbols"]) > 0:
            return res["symbols"][0]
        return {}

    def format_quantity(self, symbol: str, quantity: float) -> str:
        """Arrotonda la quantit in base allo stepSize del simbolo."""
        override = get_neural_override("BinanceAdapter.format_quantity")
        if override: return override(self, symbol, quantity)
        
        info = self.get_symbol_info(symbol)
        if not info: return str(quantity)
        
        lot_size = next((f for f in info.get("filters", []) if f["filterType"] == "LOT_SIZE"), None)
        if not lot_size: return str(quantity)
        
        step_size = float(lot_size["stepSize"])
        # Calcolo precisione: stepSize = 0.01 -> precision = 2
        import math
        precision = int(-math.log10(step_size)) if step_size < 1 else 0
        
        # Arrotonda per difetto per evitare errori di saldo insufficiente
        rounded_qty = math.floor(quantity * (10 ** precision)) / (10 ** precision)
        # Formattazione stringa per evitare notazione scientifica
        return "{:0.{}f}".format(rounded_qty, precision)

    def place_market_order(self, symbol: str, side: str, quote_order_qty: float) -> dict:
        """Esegue ordine market con gestione precisione LOT_SIZE."""
        override = get_neural_override("BinanceAdapter.place_market_order")
        if override: return override(self, symbol, side, quote_order_qty)
        
        params = {"symbol": symbol, "side": side.upper(), "type": "MARKET"}
        
        if side.upper() == "BUY":
            # Per il BUY Binance permette l'arrotondamento a 2 decimali sul quoteOrderQty
            params["quoteOrderQty"] = str(round(quote_order_qty, 2))
        else:
            # Per il SELL dobbiamo usare la QUANTITY arrotondata secondo lo stepSize
            formatted_qty = self.format_quantity(symbol, quote_order_qty)
            params["quantity"] = formatted_qty
            logger.info("Trading Prep", symbol=symbol, side=side, raw_qty=quote_order_qty, formatted_qty=formatted_qty)
            
        res = self._request("POST", "/api/v3/order", params, private=True)
        
        if "_error_internal" in res:
            return {"ok": False, "error": res["_error_internal"]}
            
        fills = res.get("fills", [])
        total_qty = sum(float(f["qty"]) for f in fills)
        total_cost = sum(float(f["qty"]) * float(f["price"]) for f in fills)
        avg_price = total_cost / total_qty if total_qty > 0 else 0
        
        return {
            "ok": True, "order_id": res.get("orderId"), "executed_qty": total_qty,
            "avg_price": avg_price, "total_cost": total_cost
        }

    def get_open_orders(self, symbol: str) -> dict:
        res = self._request("GET", "/api/v3/openOrders", {"symbol": symbol}, private=True)
        return {"ok": True, "orders": res} if isinstance(res, list) else {"ok": False, "error": res}

    def cancel_all_open_orders(self, symbol: str) -> dict:
        """Cancella tutti gli ordini aperti per un simbolo specifico."""
        res = self._request("DELETE", "/api/v3/openOrders", {"symbol": symbol}, private=True)
        return {"ok": True, "result": res} if isinstance(res, list) or "symbol" in res else {"ok": False, "error": res}

    def emergency_liquidate_all(self, quote_asset: str = "EUR") -> dict:
        """
        ORDINE NUCLEARE: Vende tutto il portafoglio (tranne quote_asset) al prezzo di mercato.
        Sincronizzato con v8.5 per massima velocit.
        """
        logger.warning(f"!!! EMERGENCY LIQUIDATE STARTING (Target: {quote_asset}) !!!")
        snapshot = self.get_account_snapshot()
        if "_error_internal" in snapshot: return {"ok": False, "error": "Could not get account snapshot"}
        
        balances = snapshot.get("balances", [])
        liquidated = []
        errors = []
        
        for b in balances:
            asset = b["asset"]
            free = float(b["free"])
            locked = float(b["locked"])
            total = free + locked
            
            if asset == quote_asset or total == 0: continue
            
            symbol = f"{asset}{quote_asset}"
            # Controlliamo il valore approssimativo per evitare piccoli 'dust'
            price_res = self.get_ticker_price(symbol)
            if price_res["ok"] and (total * price_res["price"] > 1.0):
                logger.info(f"Liquidazione d'emergenza: {symbol} (Qty: {total})")
                # 1. Cancella ordini aperti
                self.cancel_all_open_orders(symbol)
                # 2. Vende tutto
                # Ricarica il snapshot dopo la cancellata ordini per avere il 'free' aggiornato
                current_acc = self.get_account_snapshot()
                updated_bal = next((x for x in current_acc.get("balances", []) if x["asset"] == asset), None)
                final_qty = float(updated_bal["free"]) if updated_bal else free
                
                order = self.place_market_order(symbol, "SELL", final_qty)
                if order.get("ok"):
                    liquidated.append(symbol)
                else:
                    errors.append(f"{symbol}: {order.get('error')}")
        
        return {"ok": len(errors) == 0, "liquidated": liquidated, "errors": errors}

    def get_my_trades(self, symbol: str, limit: int = 5) -> dict:
        res = self._request("GET", "/api/v3/myTrades", {"symbol": symbol, "limit": limit}, private=True)
        return {"ok": True, "trades": res} if isinstance(res, list) else {"ok": False, "error": res}
