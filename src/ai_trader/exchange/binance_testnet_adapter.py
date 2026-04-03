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
        """Hmac config per richieste private (# 2026-04-03 01:05)"""
        if not self.api_secret:
            return ""
        query_string = urlencode(params)
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
            params["timestamp"] = int(time.time() * 1000)
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
