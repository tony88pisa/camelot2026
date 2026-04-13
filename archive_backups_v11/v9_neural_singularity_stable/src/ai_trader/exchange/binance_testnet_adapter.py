# src/ai_trader/exchange/binance_testnet_adapter.py
# 2026-04-03 01:05 - Binance Testnet Adapter
"""
Adapter per interagire con il flusso Spot Binance in Testnet.
Espone solo azioni in Read-Only, protegge le chiavi e non permette trade live.
"""

import hashlib
import hmac
import time
from urllib.parse import urlencode

import requests

from ai_trader.config.settings import get_settings
from ai_trader.logging.jsonl_logger import get_logger

# 2026-04-03 01:05 - Logger isolation
logger = get_logger("binance_adapter")


class BinanceTestnetAdapter:
    """
    Adapter HTTP sincrono per Binance Spot Testnet.
    Usa 'requests' per un design solido ed essenziale.
    # 2026-04-03 01:05
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None
    ):
        settings = get_settings()
        self.base_url = (base_url or settings.BINANCE_TESTNET_BASE_URL).rstrip("/")
        self.api_key = api_key or settings.BINANCE_TESTNET_API_KEY
        self.api_secret = api_secret or settings.BINANCE_TESTNET_API_SECRET
        
        # Internal HTTP session per reuse connection pools
        self.session = requests.Session()
        
        logger.info("BinanceTestnetAdapter instanziato", base_url=self.base_url)

    def _has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def _sign_payload(self, params: dict) -> str:
        """Hmac config per richieste private con supporto recvWindow (# 2026-04-12)"""
        if not self.api_secret:
            return ""
        
        # Rimuove signature se presente per evitare double-signing
        clean_params = {k: v for k, v in params.items() if k != "signature"}
        query_string = urlencode(clean_params)
        
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get(self, endpoint: str, params: dict = None, private: bool = False) -> dict:
        """
        Generic GET Request Handler
        Racchiude logicamente signature & exception safe handling.
        """
        params = params or {}
        headers = {}

        if private:
            if not self._has_credentials():
                return {"_error_internal": "auth_missing"}
            
            headers["X-MBX-APIKEY"] = self.api_key
            if "timestamp" not in params:
                params["timestamp"] = int(time.time() * 1000)
            if "recvWindow" not in params:
                params["recvWindow"] = 5000
                
            params["signature"] = self._sign_payload(params)
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                try:
                    err_msg = resp.json().get("msg", resp.text)
                except Exception:
                    err_msg = resp.text
                return {"_error_internal": f"HTTP {resp.status_code}: {err_msg}"}
        except requests.exceptions.RequestException as e:
            return {"_error_internal": str(e)}

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Converte standard tipo BTC/USDT a stringa flat BTCUSDT
        # 2026-04-03 01:05
        """
        return symbol.replace("/", "").replace("-", "").replace("_", "").upper()

    def get_server_time(self) -> dict:
        """
        Endpoint Pubblico: Restituisce l'ora del server remoto.
        # 2026-04-03 01:05
        """
        from datetime import datetime, timezone
        logger.info("Chiamata: get_server_time")

        res = self._get("/api/v3/time")
        if "_error_internal" in res:
            return {
                "ok": False,
                "source": "binance_testnet",
                "status": "unavailable",
                "error": res["_error_internal"]
            }

        server_ms = res.get("serverTime", 0)
        iso_format = datetime.fromtimestamp(server_ms / 1000.0, timezone.utc).isoformat()
        return {
            "ok": True,
            "source": "binance_testnet",
            "server_time": server_ms,
            "server_time_iso": iso_format,
            "status": "ok",
            "error": None
        }

    def get_exchange_info(self, symbol: str | None = None) -> dict:
        """
        Endpoint Pubblico: Mappa degli asset tollerati, decifrata limitazione o ruleset di Binance
        # 2026-04-03 01:05
        """
        logger.info("Chiamata: get_exchange_info", symbol=symbol)
        params = {}
        if symbol:
            params["symbol"] = self._normalize_symbol(symbol)
            
        res = self._get("/api/v3/exchangeInfo", params=params)
        if "_error_internal" in res:
            return {
                "ok": False,
                "source": "binance_testnet",
                "status": "unavailable",
                "error": res["_error_internal"]
            }
            
        return {
            "ok": True,
            "source": "binance_testnet",
            "status": "ok",
            "symbols_count": len(res.get("symbols", [])),
            "payload": res,
            "error": None
        }

    def get_ticker_price(self, symbol: str) -> dict:
        """
        Endpoint Pubblico: Fetching prezzo istantaneo (Symbol Price Ticker).
        # 2026-04-03 01:05
        """
        norm_symbol = self._normalize_symbol(symbol)
        logger.info("Chiamata: get_ticker_price", symbol=norm_symbol)
        
        res = self._get("/api/v3/ticker/price", params={"symbol": norm_symbol})
        if "_error_internal" in res:
            return {
                "ok": False,
                "source": "binance_testnet",
                "symbol": norm_symbol,
                "status": "unavailable",
                "error": res["_error_internal"]
            }

        price_str = res.get("price", "0")
        try:
            price_val = float(price_str)
        except ValueError:
            price_val = 0.0

        return {
            "ok": True,
            "source": "binance_testnet",
            "symbol": norm_symbol,
            "price": price_val,
            "status": "ok",
            "error": None
        }

    def get_account_snapshot(self) -> dict:
        """
        Endpoint Privato: Richiede Balance in testnet.
        # 2026-04-03 01:05
        """
        logger.info("Chiamata: get_account_snapshot")
        res = self._get("/api/v3/account", private=True)
        
        if "_error_internal" in res:
            err = res["_error_internal"]
            status = "auth_missing" if err == "auth_missing" else "unavailable"
            if "Invalid API-key" in err or "Signature" in err:
                status = "auth_failed"
                
            return {
                "ok": False,
                "source": "binance_testnet",
                "mode": "testnet",
                "account_type": None,
                "balances": [],
                "status": status,
                "error": err
            }

        raw_balances = res.get("balances", [])
        clean_balances = []
        for b in raw_balances:
            try:
                free = float(b.get("free", 0))
                locked = float(b.get("locked", 0))
                if free > 0 or locked > 0:
                    clean_balances.append({
                        "asset": b.get("asset"),
                        "free": free,
                        "locked": locked
                    })
            except ValueError:
                pass
                
        return {
            "ok": True,
            "source": "binance_testnet",
            "mode": "testnet",
            "account_type": res.get("accountType", "spot_testnet"),
            "balances": clean_balances,
            "status": "ok",
            "error": None
        }

    def health_check(self) -> dict:
        """
        Verifica completa del path.
        # 2026-04-03 01:05
        """
        logger.info("Chiamata: health_check")
        
        # 1. Check keys setup
        keys_setup = self._has_credentials()
        
        # 2. Check public path
        pub_check = self.get_server_time()
        pub_ok = pub_check["ok"]
        
        # 3. Check private path (only if pub path is alive and keys are loaded)
        priv_ok = False
        if pub_ok and keys_setup:
            priv_check = self.get_account_snapshot()
            priv_ok = priv_check["ok"]

        status = "ready"
        if not keys_setup and pub_ok:
            status = "partial"
        elif not pub_ok:
            status = "unavailable"
            
        return {
            "ok": pub_ok,
            "source": "binance_testnet",
            "reachable": pub_ok,
            "api_keys_configured": keys_setup,
            "public_endpoints_available": pub_ok,
            "private_endpoints_available": priv_ok,
            "status": status,
            "error": pub_check["error"] if not pub_ok else None
        }

    def get_klines(self, symbol: str, interval: str = "15m", limit: int = 50) -> list | dict:
        """
        Endpoint Pubblico: Candlestick/Klines data per analisi tecnica.
        # 2026-04-12
        
        Returns:
            Lista di candele [[open_time, open, high, low, close, volume, ...], ...]
            Oppure dict con _error_internal in caso di errore.
        """
        norm_symbol = self._normalize_symbol(symbol)
        logger.info("Chiamata: get_klines", symbol=norm_symbol, interval=interval, limit=limit)
        
        res = self._get("/api/v3/klines", params={
            "symbol": norm_symbol,
            "interval": interval,
            "limit": limit
        })
        
        if isinstance(res, dict) and "_error_internal" in res:
            return res
        
        if isinstance(res, list):
            return res
        
        return {"_error_internal": "Unexpected klines response format"}

    def place_test_order(self, symbol: str, side: str, quote_order_qty: float) -> dict:
        """
        Endpoint Privato: Invia un test order (non viene eseguito, solo validazione).
        Utile per verificare che la firma e i parametri siano corretti.
        # 2026-04-12
        """
        norm_symbol = self._normalize_symbol(symbol)
        logger.info("Chiamata: place_test_order", symbol=norm_symbol, side=side, qty=quote_order_qty)
        
        params = {
            "symbol": norm_symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quoteOrderQty": str(quote_order_qty)
        }
        
        res = self._post("/api/v3/order/test", params=params, private=True)
        
        if "_error_internal" in res:
            return {
                "ok": False,
                "source": "binance_testnet",
                "symbol": norm_symbol,
                "status": "test_order_failed",
                "error": res["_error_internal"]
            }
        
        return {
            "ok": True,
            "source": "binance_testnet",
            "symbol": norm_symbol,
            "status": "test_order_ok",
            "error": None
        }

    def place_market_order(self, symbol: str, side: str, quote_order_qty: float) -> dict:
        """
        Endpoint Privato: Esegue un ordine MARKET reale.
        Usando quoteOrderQty per specificare l'importo in USDT da spendere.
        # 2026-04-12
        
        Args:
            symbol: Pair (es. DOGEUSDT)
            side: "BUY" o "SELL"
            quote_order_qty: Importo in quote currency (es. 10.0 USDT)
            
        Returns:
            Dict con dettagli dell'ordine eseguito
        """
        norm_symbol = self._normalize_symbol(symbol)
        logger.info("Chiamata: place_market_order", symbol=norm_symbol, side=side, qty=quote_order_qty)
        
        # Safety check
        if quote_order_qty <= 0:
            return {"ok": False, "error": "quote_order_qty must be > 0", "status": "invalid"}
        
        params = {
            "symbol": norm_symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quoteOrderQty": str(round(quote_order_qty, 2))
        }
        
        # Per ordini SELL, usiamo quantity invece di quoteOrderQty
        if side.upper() == "SELL":
            del params["quoteOrderQty"]
            # Per SELL, il caller deve passare la quantity base come quote_order_qty
            params["quantity"] = str(quote_order_qty)
        
        res = self._post("/api/v3/order", params=params, private=True)
        
        if "_error_internal" in res:
            return {
                "ok": False,
                "source": "binance_testnet",
                "symbol": norm_symbol,
                "side": side.upper(),
                "status": "order_failed",
                "error": res["_error_internal"]
            }
        
        # Parse fill info
        fills = res.get("fills", [])
        avg_price = 0.0
        total_qty = 0.0
        total_cost = 0.0
        
        for fill in fills:
            qty = float(fill.get("qty", 0))
            px = float(fill.get("price", 0))
            total_qty += qty
            total_cost += qty * px
        
        if total_qty > 0:
            avg_price = total_cost / total_qty
        
        return {
            "ok": True,
            "source": "binance_testnet",
            "symbol": norm_symbol,
            "side": side.upper(),
            "order_id": res.get("orderId"),
            "status": res.get("status", "FILLED"),
            "executed_qty": total_qty,
            "avg_price": avg_price,
            "total_cost": total_cost,
            "fills": fills,
            "raw": res,
            "error": None
        }

    def _post(self, endpoint: str, params: dict = None, private: bool = False) -> dict:
        """
        Generic POST Request Handler con signature.
        # 2026-04-12
        """
        params = params or {}
        headers = {}
        
        if private:
            if not self._has_credentials():
                return {"_error_internal": "auth_missing"}
            
            headers["X-MBX-APIKEY"] = self.api_key
            if "timestamp" not in params:
                params["timestamp"] = int(time.time() * 1000)
            if "recvWindow" not in params:
                params["recvWindow"] = 5000
                
            params["signature"] = self._sign_payload(params)
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            resp = self.session.post(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            else:
                try:
                    err_msg = resp.json().get("msg", resp.text)
                except Exception:
                    err_msg = resp.text
                return {"_error_internal": f"HTTP {resp.status_code}: {err_msg}"}
        except requests.exceptions.RequestException as e:
            return {"_error_internal": str(e)}

    def get_open_orders(self, symbol: str | None = None) -> dict:
        """
        Endpoint Privato: Recupera gli ordini aperti dal server di Binance.
        # 2026-04-12
        """
        params = {}
        if symbol:
            params["symbol"] = self._normalize_symbol(symbol)
            
        logger.info("Chiamata: get_open_orders", symbol=symbol)
        res = self._get("/api/v3/openOrders", params=params, private=True)
        
        if "_error_internal" in res:
            return {
                "ok": False,
                "source": "binance_testnet",
                "orders": [],
                "error": res["_error_internal"]
            }
            
        return {
            "ok": True,
            "source": "binance_testnet",
            "orders": res,
            "error": None
        }
    def get_my_trades(self, symbol: str, limit: int = 5) -> dict:
        """
        Endpoint Privato: Recupera lo storico dei trade eseguiti (trades che sono andati a segno).
        # 2026-04-12
        """
        norm_symbol = self._normalize_symbol(symbol)
        params = {
            "symbol": norm_symbol,
            "limit": limit
        }
        
        logger.info("Chiamata: get_my_trades", symbol=norm_symbol)
        res = self._get("/api/v3/myTrades", params=params, private=True)
        
        if "_error_internal" in res:
            return {
                "ok": False,
                "source": "binance_testnet",
                "trades": [],
                "error": res["_error_internal"]
            }
            
        return {
            "ok": True,
            "source": "binance_testnet",
            "trades": res,
            "error": None
        }
