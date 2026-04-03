# src/ai_trader/mcp/registry.py
# 2026-04-02 22:28 - Registry per i tool MCP
"""
ToolRegistry — registro centralizzato dei tool disponibili.

Funzionalità:
- Registrazione tool con validazione
- Lookup per nome
- Generazione lista schema Ollama per tutti i tool registrati
- Esecuzione tool per nome con parametri
"""

from typing import Any

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.mcp.tool_base import BaseTool

# 2026-04-02 22:28 - Logger per il registry
logger = get_logger("mcp_registry")


class ToolRegistry:
    """
    Registro centralizzato dei tool MCP.
    I tool registrati vengono esposti al modello Ollama come funzioni chiamabili.
    # 2026-04-02 22:28 - Creazione classe ToolRegistry
    """

    def __init__(self):
        """# 2026-04-02 22:28"""
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Registra un tool nel registry.
        Valida che il tool implementi l'interfaccia BaseTool.
        # 2026-04-02 22:28

        Args:
            tool: istanza di BaseTool da registrare

        Raises:
            TypeError: se tool non è istanza di BaseTool
            ValueError: se un tool con lo stesso nome è già registrato
        """
        if not isinstance(tool, BaseTool):
            raise TypeError(
                f"Il tool deve essere un'istanza di BaseTool, ricevuto: {type(tool).__name__}"
            )
        if tool.name in self._tools:
            raise ValueError(
                f"Tool '{tool.name}' già registrato. Usa unregister() prima di ri-registrare."
            )

        self._tools[tool.name] = tool
        logger.info("Tool registrato", tool_name=tool.name)

    def unregister(self, name: str) -> bool:
        """
        Rimuove un tool dal registry.
        # 2026-04-02 22:28

        Args:
            name: nome del tool da rimuovere

        Returns:
            True se il tool è stato rimosso, False se non esisteva
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("Tool rimosso", tool_name=name)
            return True
        return False

    def get(self, name: str) -> BaseTool | None:
        """
        Ritorna il tool con il nome specificato, o None se non trovato.
        # 2026-04-02 22:28
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """Verifica se un tool con il nome dato è registrato. # 2026-04-02 22:28"""
        return name in self._tools

    def list_names(self) -> list[str]:
        """Ritorna l'elenco dei nomi dei tool registrati. # 2026-04-02 22:28"""
        return list(self._tools.keys())

    def get_ollama_schemas(self) -> list[dict[str, Any]]:
        """
        Genera la lista di schema tool nel formato Ollama.
        Da passare al parametro `tools` di OllamaClient.chat().
        # 2026-04-02 22:28
        """
        return [tool.to_ollama_schema() for tool in self._tools.values()]

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Esegue un tool per nome con i parametri forniti.
        # 2026-04-02 22:28

        Args:
            name: nome del tool da eseguire
            arguments: parametri da passare al tool

        Returns:
            dict con il risultato dell'esecuzione
        """
        tool = self._tools.get(name)
        if tool is None:
            logger.warning("Tool non trovato", tool_name=name)
            return {
                "ok": False,
                "result": None,
                "error": f"Tool '{name}' non trovato nel registry",
            }

        try:
            logger.info(
                "Esecuzione tool",
                tool_name=name,
                arg_keys=list(arguments.keys()),
            )
            result = tool.execute(**arguments)
            logger.info(
                "Tool eseguito",
                tool_name=name,
                ok=result.get("ok", False),
            )
            return result
        except Exception as e:
            logger.error(
                "Errore esecuzione tool",
                tool_name=name,
                error_type=type(e).__name__,
                error_msg=str(e),
            )
            return {
                "ok": False,
                "result": None,
                "error": f"Errore in '{name}': {type(e).__name__}: {e}",
            }

    @property
    def count(self) -> int:
        """Numero di tool registrati. # 2026-04-02 22:28"""
        return len(self._tools)

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"<ToolRegistry tools={self.list_names()}>"
