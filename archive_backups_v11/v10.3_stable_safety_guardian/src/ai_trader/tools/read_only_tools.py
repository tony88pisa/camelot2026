# src/ai_trader/tools/read_only_tools.py
# 2026-04-03 00:55 - Tools passivi
"""
Implementazioni concrete dei trading tool read-only per il bot.
I tool sono esposti all'MCP Orchestrator.
"""

from datetime import datetime, timezone
from typing import Any

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.memory.retrieval import MemoryRetrieval
from ai_trader.tools.base_trading_tools import BaseTradingTool

# 2026-04-03 00:55 - Logger specializzato
logger = get_logger("ro_tools")


class GetSystemTimeTool(BaseTradingTool):
    """
    Ritorna al modello lo stato del tempo corrente in formato ISO e timezone.
    Utile per ancorare logicamente episodi/eventi attuali alle memorie del parser.
    # 2026-04-03 00:55
    """

    @property
    def name(self) -> str:
        return "get_system_time"

    @property
    def description(self) -> str:
        return "Restituisce il timestamp corrente, timezone e isoformat del sistema."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        logger.info("Chiamata tool: get_system_time")
        now = datetime.now(timezone.utc)
        return {
            "ok": True,
            "result": {
                "timestamp": now.timestamp(),
                "isoformat": now.isoformat(),
                "timezone": "UTC"
            }
        }


class GetMemoryContextTool(BaseTradingTool):
    """
    Motore di Retrieval standard.
    Costruisce l'aggregato query-centrico per pattern e lezioni passate.
    # 2026-04-03 00:55
    """

    def __init__(self, retrieval: MemoryRetrieval | None = None):
        self.retrieval = retrieval or MemoryRetrieval()

    @property
    def name(self) -> str:
        return "get_memory_context"

    @property
    def description(self) -> str:
        return "Interroga la memoria del bot per episodi e lezioni utili. Da usare per cercare pattern ed eventi passati correlati a una situazione o per prendere spunto prima di decisioni importanti."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Stringa di testo o concetto da cercare in memoria."},
                "category": {"type": "string", "description": "Opzionale. Es. 'trading', 'system', 'research'."},
                "limit": {"type": "integer", "description": "Num. massimo di hit (default 5)."}
            },
            "required": ["query"]
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        query = kwargs.get("query", "")
        category = kwargs.get("category")
        limit = kwargs.get("limit", 5)

        logger.info("Chiamata tool: get_memory_context", query=query, category=category)
        try:
            ctx = self.retrieval.build_memory_context(query=query, category=category, limit=limit)
            return {"ok": True, "result": ctx}
        except Exception as e:
            logger.error("Errore chiamando Memory Retrieval", error_msg=str(e))
            return {"ok": False, "error": str(e), "result": {}}


class GetRecentEpisodesTool(BaseTradingTool):
    """
    Ritorna in blocco l'andamento cronologico grezzo recente dell'ultima giornata
    nella categoria Trading. Non usa filtering.
    # 2026-04-03 00:55
    """

    def __init__(self, retrieval: MemoryRetrieval | None = None):
        self.retrieval = retrieval or MemoryRetrieval()

    @property
    def name(self) -> str:
        return "get_recent_trading_episodes"

    @property
    def description(self) -> str:
        return "Legge gli episodi crudi e intatti verificatisi pi di recente in ambito trading (es. scan asincroni o trades passati prossimi). Non effettua ricerche."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Massimo log da mostrare (default 10)."}
            },
            "required": []
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        limit = kwargs.get("limit", 10)
        logger.info("Chiamata tool: get_recent_trading_episodes", limit=limit)

        try:
            raw_eps = self.retrieval.episodes.load_episodes("trading")
            raw_eps.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            subset = raw_eps[:limit]
            
            compact = []
            for ep in subset:
                compact.append({
                    "timestamp": ep.get("timestamp"),
                    "kind": ep.get("kind"),
                    "payload": ep.get("payload")
                })

            return {"ok": True, "result": compact}
        except Exception as e:
            logger.error("Errore recupero episodi", error_msg=str(e))
            return {"ok": False, "error": str(e), "result": []}


class GetRecentLessonsTool(BaseTradingTool):
    """
    Ritorna le lezioni recenti, indipendentemente dal retrieval scoring,
    come promemoria di contesto operativo.
    # 2026-04-03 00:55
    """

    def __init__(self, retrieval: MemoryRetrieval | None = None):
        self.retrieval = retrieval or MemoryRetrieval()

    @property
    def name(self) -> str:
        return "get_recent_lessons"

    @property
    def description(self) -> str:
        return "Recupera i log di sintesi finali formatisi di recente per acquisire insights senza filtro semantico o ricerca profonda."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Es. 'trading' o 'system'."},
                "limit": {"type": "integer", "description": "Default 10."}
            },
            "required": []
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        category = kwargs.get("category", "trading")
        limit = kwargs.get("limit", 10)
        logger.info("Chiamata tool: get_recent_lessons", category=category, limit=limit)

        try:
            les_meta = self.retrieval.lessons.read_lessons(category)
            # Reverses to simulate recent first assuming sorted glob is somewhat chronologically linear or by parsing
            # Per design il MD filename  `YYYY-MM-DD-lesson-00x` quindi lexically sortable
            les_meta.sort(key=lambda x: x.get("filename", ""), reverse=True)
            subset = les_meta[:limit]

            compact = []
            for l in subset:
                compact.append({
                    "title": l.get("title"),
                    "filename": l.get("filename")
                })
            return {"ok": True, "result": compact}
        except Exception as e:
            logger.error("Errore recupero lezioni", error_msg=str(e))
            return {"ok": False, "error": str(e), "result": []}


class GetMarketSnapshotStubTool(BaseTradingTool):
    """
    Ritorna mockup dati del mercato utili per mantenere integro lo skeleton del LLM.
    Prossimo passo sar cablare questo a Binance API.
    # 2026-04-03 00:55
    """

    @property
    def name(self) -> str:
        return "get_market_snapshot_stub"

    @property
    def description(self) -> str:
        return "Restituisce un abstract / snapshot fittizio dei prezzi di mercato real (STUB). Nessun ordine o reale retrieval viene effettuato tramite API esterna."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Pair di trading (Es. 'BTC/USDT')"}
            },
            "required": ["symbol"]
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        symbol = kwargs.get("symbol", "UNKNOWN").upper()
        logger.info("Chiamata tool: get_market_snapshot_stub", symbol=symbol)
        
        # Stub prices for simulation realism
        mock_prices = {
            "BTC/USDT": 98500.00,
            "ETH/USDT": 3400.00,
            "SOL/USDT": 230.50
        }
        
        price = mock_prices.get(symbol, 1.00)

        return {
            "ok": True,
            "result": {
                "symbol": symbol,
                "price": price,
                "source": "stub_memory_layer",
                "status": "stub",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        }


class GetMarketSnapshotTool(BaseTradingTool):
    """
    Ritorna dati reali del mercato (o fallback) usando il Binance Adapter.
    # 2026-04-03 01:05
    """
    def __init__(self, adapter=None):
        from ai_trader.exchange.binance_testnet_adapter import BinanceTestnetAdapter
        self.adapter = adapter or BinanceTestnetAdapter()
        self.stub_fallback = GetMarketSnapshotStubTool()

    @property
    def name(self) -> str:
        return "get_market_snapshot"

    @property
    def description(self) -> str:
        return "Restituisce il prezzo corrente reale dal Binance Testnet Spot. Se l'exchange  irraggiungibile usa un fallback locale."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Pair di trading (Es. 'BTC/USDT')"}
            },
            "required": ["symbol"]
        }

    def execute(self, **kwargs: Any) -> dict[str, Any]:
        symbol = kwargs.get("symbol", "UNKNOWN").upper()
        logger.info("Chiamata tool: get_market_snapshot", symbol=symbol)
        
        res = self.adapter.get_ticker_price(symbol)
        if res.get("ok"):
            return {
                "ok": True,
                "result": {
                    "symbol": res.get("symbol"),
                    "price": res.get("price"),
                    "source": res.get("source"),
                    "status": "live",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
        else:
            logger.warning("Binance fetching fallito, uso stub logic", reason=res.get("error"))
            return self.stub_fallback.execute(**kwargs)
