# tests/test_mcp_core.py
# 2026-04-02 22:29 - Test suite per il modulo MCP Core
# Copre: BaseTool, ToolRegistry, MCPOrchestrator
"""
Test suite per src/ai_trader/mcp/

Copre:
- BaseTool: creazione tool concreti, schema Ollama
- ToolRegistry: register/unregister/get, esecuzione, validazione
- MCPOrchestrator: ciclo senza tool, con tool mock, gestione errori
"""

import json
import urllib.error
import urllib.request

import pytest

from ai_trader.mcp.tool_base import BaseTool
from ai_trader.mcp.registry import ToolRegistry
from ai_trader.mcp.orchestrator import MCPOrchestrator
from ai_trader.core.ollama_client import OllamaClient


# ==============================================================================
# Helper: tool concreto di test  2026-04-02 22:29
# ==============================================================================
class EchoTool(BaseTool):
    """Tool di test che ritorna l'input ricevuto. # 2026-04-02 22:29"""

    @property
    def name(self) -> str:
        return "echo"

    @property
    def description(self) -> str:
        return "Ritorna il messaggio ricevuto"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Messaggio da ripetere"},
            },
            "required": ["message"],
        }

    def execute(self, **kwargs) -> dict:
        msg = kwargs.get("message", "")
        return {"ok": True, "result": f"echo: {msg}"}


class FailingTool(BaseTool):
    """Tool che fallisce sempre, per testare la gestione errori. # 2026-04-02 22:29"""

    @property
    def name(self) -> str:
        return "always_fail"

    @property
    def description(self) -> str:
        return "Tool che fallisce sempre"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs) -> dict:
        raise RuntimeError("Errore intenzionale per test")


class AddTool(BaseTool):
    """Tool che somma due numeri. # 2026-04-02 22:29"""

    @property
    def name(self) -> str:
        return "add_numbers"

    @property
    def description(self) -> str:
        return "Somma due numeri e ritorna il risultato"

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "Primo numero"},
                "b": {"type": "number", "description": "Secondo numero"},
            },
            "required": ["a", "b"],
        }

    def execute(self, **kwargs) -> dict:
        a = kwargs.get("a", 0)
        b = kwargs.get("b", 0)
        return {"ok": True, "result": a + b}


# ==============================================================================
# Helper per rilevare Ollama  2026-04-02 22:29
# ==============================================================================
_OLLAMA_AVAILABLE_MODEL: str | None = None


def _detect_ollama() -> bool:
    """# 2026-04-02 22:29"""
    global _OLLAMA_AVAILABLE_MODEL
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status != 200:
                return False
            data = json.loads(resp.read().decode())
            models = data.get("models", [])
            if models:
                sorted_models = sorted(models, key=lambda m: m.get("size", float("inf")))
                _OLLAMA_AVAILABLE_MODEL = sorted_models[0].get("name")
            return True
    except Exception:
        return False


OLLAMA_LIVE = _detect_ollama()
skip_no_ollama = pytest.mark.skipif(
    not OLLAMA_LIVE,
    reason="Ollama non raggiungibile  test live skippato",
)


# ==============================================================================
# TEST: BaseTool  2026-04-02 22:29
# ==============================================================================
class TestBaseTool:
    """Test per BaseTool e to_ollama_schema(). # 2026-04-02 22:29"""

    def test_echo_tool_properties(self):
        """EchoTool ha le propriet corrette."""
        tool = EchoTool()
        assert tool.name == "echo"
        assert tool.description != ""
        assert "properties" in tool.parameters

    def test_echo_tool_execute(self):
        """EchoTool.execute() ritorna risultato corretto."""
        tool = EchoTool()
        result = tool.execute(message="hello")
        assert result["ok"] is True
        assert "hello" in result["result"]

    def test_ollama_schema_format(self):
        """to_ollama_schema() genera lo schema nel formato Ollama corretto."""
        tool = EchoTool()
        schema = tool.to_ollama_schema()
        assert schema["type"] == "function"
        assert "function" in schema
        func = schema["function"]
        assert func["name"] == "echo"
        assert func["description"] != ""
        assert "parameters" in func
        assert func["parameters"]["type"] == "object"

    def test_add_tool_execute(self):
        """AddTool.execute() calcola correttamente."""
        tool = AddTool()
        result = tool.execute(a=3, b=7)
        assert result["ok"] is True
        assert result["result"] == 10

    def test_tool_repr(self):
        """Tool ha un __repr__ leggibile."""
        tool = EchoTool()
        assert "echo" in repr(tool)

    def test_cannot_instantiate_abstract(self):
        """Non si pu istanziare BaseTool direttamente."""
        with pytest.raises(TypeError):
            BaseTool()  # type: ignore


# ==============================================================================
# TEST: ToolRegistry  2026-04-02 22:29
# ==============================================================================
class TestToolRegistry:
    """Test per ToolRegistry. # 2026-04-02 22:29"""

    def test_register_and_get(self):
        """Registrare un tool e recuperarlo per nome."""
        registry = ToolRegistry()
        registry.register(EchoTool())
        assert registry.has("echo")
        assert registry.get("echo") is not None
        assert registry.count == 1

    def test_register_duplicate_raises(self):
        """Registrare lo stesso nome due volte solleva ValueError."""
        registry = ToolRegistry()
        registry.register(EchoTool())
        with pytest.raises(ValueError, match="gi registrato"):
            registry.register(EchoTool())

    def test_register_invalid_type_raises(self):
        """Registrare un oggetto non-BaseTool solleva TypeError."""
        registry = ToolRegistry()
        with pytest.raises(TypeError, match="BaseTool"):
            registry.register("not a tool")  # type: ignore

    def test_unregister(self):
        """Unregister rimuove un tool registrato."""
        registry = ToolRegistry()
        registry.register(EchoTool())
        assert registry.unregister("echo") is True
        assert registry.has("echo") is False
        assert registry.count == 0

    def test_unregister_nonexistent(self):
        """Unregister di un tool inesistente ritorna False."""
        registry = ToolRegistry()
        assert registry.unregister("nonexistent") is False

    def test_get_nonexistent(self):
        """Get di un tool inesistente ritorna None."""
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_list_names(self):
        """list_names ritorna i nomi dei tool registrati."""
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(AddTool())
        names = registry.list_names()
        assert "echo" in names
        assert "add_numbers" in names
        assert len(names) == 2

    def test_get_ollama_schemas(self):
        """get_ollama_schemas genera schema validi per tutti i tool."""
        registry = ToolRegistry()
        registry.register(EchoTool())
        registry.register(AddTool())
        schemas = registry.get_ollama_schemas()
        assert len(schemas) == 2
        for s in schemas:
            assert s["type"] == "function"
            assert "function" in s

    def test_execute_tool_success(self):
        """execute_tool esegue il tool correttamente."""
        registry = ToolRegistry()
        registry.register(EchoTool())
        result = registry.execute_tool("echo", {"message": "test"})
        assert result["ok"] is True
        assert "test" in result["result"]

    def test_execute_tool_not_found(self):
        """execute_tool con nome inesistente ritorna errore."""
        registry = ToolRegistry()
        result = registry.execute_tool("nonexistent", {})
        assert result["ok"] is False
        assert "non trovato" in result["error"]

    def test_execute_tool_handles_exception(self):
        """execute_tool gestisce eccezioni del tool senza crash."""
        registry = ToolRegistry()
        registry.register(FailingTool())
        result = registry.execute_tool("always_fail", {})
        assert result["ok"] is False
        assert "RuntimeError" in result["error"]

    def test_len(self):
        """len() funziona sul registry."""
        registry = ToolRegistry()
        assert len(registry) == 0
        registry.register(EchoTool())
        assert len(registry) == 1


# ==============================================================================
# TEST: MCPOrchestrator  2026-04-02 22:29
# ==============================================================================
class TestMCPOrchestrator:
    """Test per MCPOrchestrator. # 2026-04-02 22:29"""

    def test_init_default(self):
        """Orchestratore si crea con default senza errori."""
        orch = MCPOrchestrator()
        assert orch.client is not None
        assert orch.registry is not None
        assert orch.max_tool_rounds > 0

    def test_init_custom(self):
        """Orchestratore accetta client e registry custom."""
        client = OllamaClient(host="10.0.0.1", port=1, timeout=1)
        registry = ToolRegistry()
        registry.register(EchoTool())
        orch = MCPOrchestrator(client=client, registry=registry, max_tool_rounds=3)
        assert orch.client is client
        assert orch.registry is registry
        assert orch.max_tool_rounds == 3

    def test_run_unreachable_returns_error(self):
        """run() con host non raggiungibile ritorna errore strutturato."""
        client = OllamaClient(host="192.0.2.1", port=1, timeout=1)
        orch = MCPOrchestrator(client=client)
        result = orch.run(messages=[{"role": "user", "content": "test"}])
        assert result["ok"] is False
        assert "error" in result
        assert result["rounds"] == 0

    @skip_no_ollama
    def test_live_simple_chat(self):
        """run() senza tool, Ollama risponde direttamente. # 2026-04-02 22:29"""
        if _OLLAMA_AVAILABLE_MODEL is None:
            pytest.skip("Nessun modello Ollama disponibile")
        client = OllamaClient(model=_OLLAMA_AVAILABLE_MODEL)
        orch = MCPOrchestrator(client=client)
        result = orch.run(
            messages=[{"role": "user", "content": "Rispondi solo: OK"}],
            max_tokens=10,
            temperature=0.0,
        )
        assert result["ok"] is True
        assert result["message"]["role"] == "assistant"
        assert result["rounds"] >= 1
        assert result["tool_calls_made"] == []

    @skip_no_ollama
    def test_live_with_tools(self):
        """run() con tool registrati, il modello potrebbe chiamare tool. # 2026-04-02 22:29"""
        if _OLLAMA_AVAILABLE_MODEL is None:
            pytest.skip("Nessun modello Ollama disponibile")

        client = OllamaClient(model=_OLLAMA_AVAILABLE_MODEL)
        registry = ToolRegistry()
        registry.register(AddTool())

        orch = MCPOrchestrator(client=client, registry=registry)
        result = orch.run(
            messages=[{"role": "user", "content": "Usa il tool add_numbers per sommare 3 e 7. Rispondi con il risultato."}],
            temperature=0.0,
            max_tokens=50,
        )
        # 2026-04-02 22:29 - Il modello potrebbe o meno usare il tool,
        # ma il flusso deve completarsi senza crash
        assert result["ok"] is True
        assert result["rounds"] >= 1
