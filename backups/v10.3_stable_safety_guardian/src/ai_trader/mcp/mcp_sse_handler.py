# src/ai_trader/mcp/mcp_sse_handler.py
import json
import requests
import re
from typing import Any, Dict, Optional, List
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("mcp_sse_handler")

class McpSseHandler:
    """
    Gestore MCP specializzato per SuperMemory (Standard Streamable HTTP 2026).
    Supporta il parsing dei messaggi JSON-RPC incapsulati in SSE data.
    """

    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
        self.session_id: Optional[str] = None
        self.base_headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "x-sm-project": "sm_project_default"
        }

    def connect(self) -> bool:
        """Inizializzazione con cattura del Session ID."""
        logger.info("Apertura sessione SuperMemory...", url=self.url)
        init_payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ai-trader", "version": "1.0.0"}
            },
            "id": 1
        }
        try:
            response = requests.post(self.url, headers=self.base_headers, json=init_payload, timeout=15)
            if response.status_code == 200:
                self.session_id = response.headers.get("Mcp-Session-Id")
                if self.session_id:
                    logger.info("Sessione stabilita", session_id=self.session_id)
                    # Notifica initialized (opzionale ma consigliata)
                    requests.post(self.url, headers=self._get_headers(), json={"jsonrpc": "2.0", "method": "notifications/initialized"}, timeout=5)
                    return True
            logger.error("Inizializzazione fallita", code=response.status_code, body=response.text[:200])
            return False
        except Exception as e:
            logger.error("Errore connessione MCP", error=str(e))
            return False

    def _get_headers(self) -> Dict[str, str]:
        headers = self.base_headers.copy()
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _parse_sse_response(self, text: str) -> Dict[str, Any]:
        """Estrae il JSON-RPC data da una risposta codificata SSE."""
        for line in text.splitlines():
            if line.startswith("data:"):
                try:
                    return json.loads(line.replace("data:", "").strip())
                except:
                    continue
        # Fallback se non  SSE
        try:
            return json.loads(text)
        except:
            return {"error": "Invalid response format"}

    def _call_rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Esegue chiamata RPC con parsing SSE."""
        if not self.session_id: return {"ok": False, "error": "No session"}
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 2}
        try:
            res = requests.post(self.url, headers=self._get_headers(), json=payload, timeout=30)
            parsed = self._parse_sse_response(res.text)
            if "error" in parsed:
                return {"ok": False, "error": parsed["error"]}
            return {"ok": True, "result": parsed.get("result", {})}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def list_tools(self) -> Dict[str, Any]:
        # Lo standard MCP 1.x usa 'tools/list'
        res = self._call_rpc("tools/list", {})
        if res.get("ok"):
            tools = res["result"].get("tools", [])
            return {"ok": True, "tools": tools}
        return res

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        # Lo standard MCP 1.x usa 'tools/call'
        return self._call_rpc("tools/call", {"name": tool_name, "arguments": arguments})
