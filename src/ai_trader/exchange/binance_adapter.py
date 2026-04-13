import decimal
import hashlib
import hmac
import time
import requests
from datetime import datetime
from urllib.parse import urlencode
from ai_trader.config.settings import get_settings
from ai_trader.logging.jsonl_logger import get_logger

# 2026-04-13 - Configurazione precisione globale per v10.7
decimal.getcontext().prec = 28

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
            resp = self.session.request(method, url, params=params, headers=headers, timeout=(5, 10))
            if resp.status_code == 200: return resp.json()
            
            err_data = resp.json()
            err = err_data.get("msg", resp.text) if resp.status_code != 404 else "Not Found"
            return {"_error_internal": f"HTTP {resp.status_code}: {err}", "code": err_data.get("code")}
        except Exception as e:
            logger.error("Binance API Exception", method=method, endpoint=endpoint, error=str(e))
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

    def get_all_prices(self) -> dict:
        """Recupera tutti i prezzi in un'unica chiamata (v10.30 Optimized)."""
        res = self._request("GET", "/api/v3/ticker/price")
        if isinstance(res, list):
            return {item["symbol"]: float(item["price"]) for item in res}
        return {}

    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 50) -> list:
        res = self._request("GET", "/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})
        return res if isinstance(res, list) else []

    def get_24h_tickers(self) -> list:
        res = self._request("GET", "/api/v3/ticker/24hr")
        return res if isinstance(res, list) else []

    def get_account_snapshot(self) -> dict:
        """Recupera il saldo grezzo da Binance (/api/v3/account)."""
        return self._request("GET", "/api/v3/account", private=True)

    def get_account_summary(self) -> dict:
        """
        Versione Normalizzata (v10.45 Sovereign Holism).
        Calcola total_wallet_value e free_quote_balance in EUR.
        """
        snap = self.get_account_snapshot()
        if "_error_internal" in snap:
            return {"ok": False, "error": snap["_error_internal"]}
            
        balances = snap.get("balances", [])
        prices = self.get_all_prices()
        
        total_eur = 0.0
        free_eur = 0.0
        
        for b in balances:
            asset = b["asset"]
            free = float(b["free"])
            locked = float(b["locked"])
            total = free + locked
            
            if total == 0: continue
            
            if asset == "EUR":
                total_eur += total
                free_eur += free
            else:
                symbol = f"{asset}EUR"
                if symbol in prices:
                    total_eur += total * prices[symbol]
                elif f"{asset}USDT" in prices and "USDTEUR" in prices:
                    # Fallback cross-price
                    total_eur += total * prices[f"{asset}USDT"] * prices["USDTEUR"]
        
        return {
            "ok": True,
            "total_wallet_value": total_eur,
            "free_quote_balance": free_eur,
            "balances": balances,
            "timestamp": datetime.now().isoformat()
        }

    def get_symbol_info(self, symbol: str) -> dict:
        """Recupera informazioni sul simbolo inclusi i filtri (LOT_SIZE, ecc)."""
        res = self._request("GET", "/api/v3/exchangeInfo", {"symbol": symbol})
        if "symbols" in res and len(res["symbols"]) > 0:
            return res["symbols"][0]
        return {}

    def format_quantity(self, symbol: str, quantity: float) -> str:
        """Applica la quantizzazione deterministica basata su LOT_SIZE e MARKET_LOT_SIZE (v10.43)."""
        info = self.get_symbol_info(symbol)
        filters = info.get("filters", [])
        
        # 2026-04-13 - Priorit MARKET_LOT_SIZE per ordini Market
        lot_filter = next((f for f in filters if f["filterType"] == "MARKET_LOT_SIZE"), None)
        if not lot_filter:
            lot_filter = next((f for f in filters if f["filterType"] == "LOT_SIZE"), None)
            
        if not lot_filter: return str(quantity)
        
        step_str = lot_filter["stepSize"]
        # Calcolo precisione reale basato sulla stringa dello stepSize
        if '.' in step_str:
            precision = len(step_str.split('.')[1].rstrip('0'))
            if precision == 0 and step_str.split('.')[1].startswith('0'):
                # Caso particolare per stepSize come '0.0010000'
                precision = len(step_str.split('.')[1].rstrip('0'))
        else:
            precision = 0

        # Quantizzazione via Decimal per evitare floating point issues
        from decimal import Decimal, ROUND_DOWN
        d_qty = Decimal(str(quantity))
        d_step = Decimal(str(step_str))
        
        # Formula: (qty / step).floor() * step
        quantized = (d_qty / d_step).quantize(Decimal('1'), rounding=ROUND_DOWN) * d_step
        
        return "{:0.{}f}".format(float(quantized), precision)

    def place_market_order(self, symbol: str, side: str, quote_order_qty: float) -> dict:
        """Esegue ordine market con gestione precisione LOT_SIZE."""
        params = {"symbol": symbol, "side": side.upper(), "type": "MARKET"}
        
        if side.upper() == "BUY":
            # Per il BUY Binance permette l'arrotondamento a 2 decimali sul quoteOrderQty
            params["quoteOrderQty"] = str(round(quote_order_qty, 2))
        else:
            # Per il SELL dobbiamo usare la QUANTITY arrotondata secondo lo stepSize
            formatted_qty = self.format_quantity(symbol, quote_order_qty)
            params["quantity"] = formatted_qty
           
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

    def get_order_book(self, symbol: str, limit: int = 100) -> dict:
        """Ottiene snapshot del libro ordini (L2)."""
        res = self._request("GET", "/api/v3/depth", {"symbol": symbol, "limit": limit})
        return res

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
