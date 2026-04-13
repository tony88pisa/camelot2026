# src/ai_trader/config/settings.py
# 2026-04-02 21:05 - Configurazione centralizzata del progetto AI Trader
# Legge variabili da .env con fallback a valori di default
"""
Configurazione centralizzata.
Tutte le impostazioni del progetto passano da qui.
"""

import os
import json
from pathlib import Path
from datetime import datetime

# 2026-04-02 21:05 - Calcolo root del progetto (3 livelli su da config/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# 2026-04-02 21:05 - Carica .env se presente (con python-dotenv se installato)
_dotenv_path = PROJECT_ROOT / ".env"
try:
    from dotenv import load_dotenv
    if _dotenv_path.exists():
        load_dotenv(_dotenv_path)
except ImportError:
    # python-dotenv non installato, usiamo solo os.environ
    pass


class Settings:
    """
    Configurazione centralizzata del progetto.
    Legge da variabili d'ambiente con fallback a valori di default.
    # 2026-04-02 21:05 - Creazione classe Settings
    """

    # --- Progetto ---
    PROJECT_NAME: str = "AI Trader"
    VERSION: str = "0.1.0"
    PROJECT_ROOT: Path = PROJECT_ROOT
    PROJECT_ENV: str = os.getenv("PROJECT_ENV", "dev")

    # --- Autonomous & Oracle Config (v5.0) ---
    AUTONOMOUS_CONFIG_PATH: Path = PROJECT_ROOT / "data" / "autonomous_config.json"
    
    def load_autonomous_config(self) -> dict:
        """Carica la configurazione generata autonomamente dall'AI."""
        if self.AUTONOMOUS_CONFIG_PATH.exists():
            try:
                with open(self.AUTONOMOUS_CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    # --- Ollama ---
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    # --- Trading Configuration ---
    # 2026-04-12 - Config per mercato Europeo (EUR Core)
    TRADING_MODE: str = os.getenv("TRADING_MODE", "testnet")
    QUOTE_CURRENCY: str = os.getenv("QUOTE_CURRENCY", "EUR")
    INITIAL_CAPITAL: float = float(os.getenv("INITIAL_CAPITAL", "50.0"))  # Valuta di base (EUR)
    MAX_ORDER_VALUE: float = float(os.getenv("MAX_ORDER_VALUE", "10.0"))
    WHITELIST_PAIRS: list[str] = os.getenv("WHITELIST_PAIRS", "SOLEUR,BTCEUR").split(",")
    CYCLE_INTERVAL_SEC: float = float(os.getenv("CYCLE_INTERVAL_SEC", "30.0"))

    # --- Grid Trading Parameters ---
    GRID_LEVELS: int = int(os.getenv("GRID_LEVELS", "8"))
    GRID_ALLOCATION_PCT: float = float(os.getenv("GRID_ALLOCATION_PCT", "0.80"))  # 80% del capitale in grid

    # Modulo 07 - Binance Testnet Settings
    # 2026-04-03 01:05
    BINANCE_TESTNET_ENABLED: bool = os.getenv("BINANCE_TESTNET_ENABLED", "true").lower() == "true"
    BINANCE_TESTNET_API_KEY: str | None = os.getenv("BINANCE_TESTNET_API_KEY")
    BINANCE_TESTNET_API_SECRET: str | None = os.getenv("BINANCE_TESTNET_API_SECRET")
    # Binance Testnet (Endpoint Ufficiale 2026)
    BINANCE_TESTNET_BASE_URL: str = "https://testnet.binance.vision"
    BINANCE_TESTNET_WS_URL: str = "wss://testnet.binance.vision/ws-api/v3"

    # --- SuperMemory MCP Configuration ---
    SUPERMEMORY_TOKEN: str = os.getenv("SUPERMEMORY_TOKEN", "")
    SUPERMEMORY_URL: str = os.getenv("SUPERMEMORY_URL", "https://mcp.supermemory.ai/mcp")

    # Binance Mainnet Settings (per passaggio a live)
    BINANCE_MAINNET_API_KEY: str | None = os.getenv("BINANCE_MAINNET_API_KEY")
    BINANCE_MAINNET_API_SECRET: str | None = os.getenv("BINANCE_MAINNET_API_SECRET")
    BINANCE_MAINNET_BASE_URL: str = os.getenv("BINANCE_MAINNET_BASE_URL", "https://api.binance.com")

    # Parse host/port da env (gestisce sia "localhost" che "http://127.0.0.1:11434")
    _raw_host = os.getenv("OLLAMA_HOST", "localhost")
    _raw_port = os.getenv("OLLAMA_PORT", "")

    @staticmethod
    def _parse_ollama_host_port(raw_host: str, raw_port: str) -> tuple[str, int]:
        """
        Estrae hostname e porta da OLLAMA_HOST, che potrebbe essere:
        - "localhost"
        - "127.0.0.1"
        - "http://127.0.0.1:11434"
        - "http://localhost:11434"
        Se OLLAMA_PORT  esplicitamente settato, usa quello.
        # 2026-04-02 21:10 - Fix URL completo in OLLAMA_HOST
        """
        from urllib.parse import urlparse
        host = raw_host.strip()
        port = 11434  # default

        if host.startswith("http://") or host.startswith("https://"):
            parsed = urlparse(host)
            host = parsed.hostname or "localhost"
            if parsed.port:
                port = parsed.port
        elif ":" in host:
            # Formato "host:port" senza schema
            parts = host.rsplit(":", 1)
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                pass

        # Se OLLAMA_PORT  esplicitamente settato, ha la precedenza
        if raw_port.strip():
            try:
                port = int(raw_port.strip())
            except ValueError:
                pass

        return host, port

    OLLAMA_HOST: str = ""
    OLLAMA_PORT: int = 11434

    def __init__(self):
        """# 2026-04-02 21:10 - Parse Ollama host/port in __init__"""
        self.OLLAMA_HOST, self.OLLAMA_PORT = self._parse_ollama_host_port(
            self._raw_host, self._raw_port
        )

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: Path = PROJECT_ROOT / os.getenv("LOG_DIR", "logs")

    # --- Paths ---
    DATA_DIR: Path = PROJECT_ROOT / "data"
    MEMDIR: Path = PROJECT_ROOT / "memdir"
    REPORTS_DIR: Path = PROJECT_ROOT / "reports"

    @property
    def ollama_base_url(self) -> str:
        """URL base di Ollama. # 2026-04-02 21:05"""
        return f"http://{self.OLLAMA_HOST}:{self.OLLAMA_PORT}"

    def ensure_dirs(self) -> None:
        """Crea le directory necessarie se non esistono. # 2026-04-02 21:05"""
        for d in [self.LOG_DIR, self.DATA_DIR, self.MEMDIR, self.REPORTS_DIR]:
            d.mkdir(parents=True, exist_ok=True)


# 2026-04-02 21:05 - Singleton per accesso rapido
_settings: Settings | None = None


def get_settings() -> Settings:
    """Restituisce l'istanza singleton di Settings. # 2026-04-02 21:05"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
