# src/ai_trader/mcp/tool_base.py
# 2026-04-02 22:28 - Classe base astratta per i tool MCP
"""
BaseTool — interfaccia standard per definire tool disponibili al modello LLM.

Ogni tool concreto deve:
1. Ereditare da BaseTool
2. Definire name, description, parameters
3. Implementare execute(**kwargs) -> dict
4. Lo schema Ollama viene generato automaticamente da to_ollama_schema()
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Interfaccia base per tutti i tool MCP.
    Ogni tool espone il proprio schema per Ollama function calling
    e un metodo execute() per l'esecuzione.
    # 2026-04-02 22:28 - Creazione classe BaseTool
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome univoco del tool (snake_case). # 2026-04-02 22:28"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Descrizione breve del tool per il modello LLM. # 2026-04-02 22:28"""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """
        Schema dei parametri in formato JSON Schema.
        Esempio:
        {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol"},
                "period": {"type": "string", "enum": ["1d","1w","1m"]}
            },
            "required": ["symbol"]
        }
        # 2026-04-02 22:28
        """
        ...

    @abstractmethod
    def execute(self, **kwargs: Any) -> dict[str, Any]:
        """
        Esegue il tool con i parametri forniti.
        Deve restituire un dict con almeno:
        - "ok": bool
        - "result": Any (dati di ritorno)
        - "error": str (se ok=False)
        # 2026-04-02 22:28
        """
        ...

    def to_ollama_schema(self) -> dict[str, Any]:
        """
        Genera lo schema tool nel formato richiesto dall'API Ollama /api/chat.
        Formato Ollama:
        {
            "type": "function",
            "function": {
                "name": "...",
                "description": "...",
                "parameters": { ... json schema ... }
            }
        }
        # 2026-04-02 22:28
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def __repr__(self) -> str:
        return f"<Tool:{self.name}>"
