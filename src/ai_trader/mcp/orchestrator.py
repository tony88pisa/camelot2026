# src/ai_trader/mcp/orchestrator.py
# 2026-04-02 22:29 - Orchestratore MCP: gestisce il ciclo chat → tool_call → result → chat
"""
MCPOrchestrator — cuore del protocollo MCP.

Gestisce il ciclo di conversazione con Ollama includendo l'esecuzione di tool:
1. Invia messaggi a Ollama con gli schema dei tool registrati
2. Se Ollama risponde con una tool_call, esegue il tool tramite il registry
3. Aggiunge il risultato alla conversazione come messaggio "tool"
4. Ripete finché Ollama risponde con contenuto testuale o si raggiunge il limite
"""

import json
from typing import Any

from ai_trader.core.ollama_client import OllamaClient
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.mcp.registry import ToolRegistry

# 2026-04-02 22:29 - Logger per l'orchestratore
logger = get_logger("mcp_orchestrator")

# 2026-04-02 22:29 - Limite massimo di iterazioni tool_call per evitare loop infiniti
DEFAULT_MAX_TOOL_ROUNDS = 5


class MCPOrchestrator:
    """
    Orchestratore del ciclo MCP: chat + tool calling.
    Collega OllamaClient e ToolRegistry in un flusso coerente.
    # 2026-04-02 22:29 - Creazione classe MCPOrchestrator
    """

    def __init__(
        self,
        client: OllamaClient | None = None,
        registry: ToolRegistry | None = None,
        max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS,
    ):
        """
        Inizializza l'orchestratore.
        # 2026-04-02 22:29

        Args:
            client: istanza OllamaClient (se None, ne crea uno con config default)
            registry: istanza ToolRegistry (se None, ne crea uno vuoto)
            max_tool_rounds: massimo numero di cicli tool_call prima di fermarsi
        """
        self.client = client or OllamaClient()
        self.registry = registry or ToolRegistry()
        self.max_tool_rounds = max_tool_rounds

        logger.info(
            "MCPOrchestrator inizializzato",
            tools_count=self.registry.count,
            max_tool_rounds=self.max_tool_rounds,
        )

    def run(
        self,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """
        Esegue il ciclo completo: chat con Ollama, gestione tool_calls, ritorno risposta finale.
        # 2026-04-02 22:29

        Args:
            messages: lista di messaggi iniziali [{"role": "user", "content": "..."}]
            temperature: temperatura di sampling
            max_tokens: massimo token in risposta

        Returns:
            dict con:
                - "ok": bool
                - "message": dict con la risposta finale dell'assistente
                - "model": str
                - "tool_calls_made": list dei tool chiamati
                - "rounds": int numero di cicli effettuati
                - "error": dict (solo se ok=False)
        """
        # 2026-04-02 22:29 - Copia messaggi per non modificare l'originale
        conversation = list(messages)
        tool_calls_made: list[dict[str, Any]] = []
        tools_schemas = self.registry.get_ollama_schemas() if self.registry.count > 0 else None

        logger.info(
            "Orchestrazione avviata",
            message_count=len(conversation),
            tools_available=self.registry.list_names(),
        )

        for round_num in range(self.max_tool_rounds + 1):
            # 2026-04-02 22:29 - Chiama Ollama
            response = self.client.chat(
                messages=conversation,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools_schemas,
            )

            if not response["ok"]:
                logger.error(
                    "Chat fallita durante orchestrazione",
                    round_num=round_num,
                    error_type=response.get("error", {}).get("error_type", "unknown"),
                )
                return {
                    "ok": False,
                    "message": {},
                    "model": response.get("model", ""),
                    "tool_calls_made": tool_calls_made,
                    "rounds": round_num,
                    "error": response.get("error", {}),
                }

            assistant_msg = response.get("message", {})

            # 2026-04-02 22:29 - Verifica se il modello ha richiesto tool_calls
            tool_calls = assistant_msg.get("tool_calls")

            if not tool_calls:
                # 2026-04-02 22:29 - Nessun tool_call: risposta finale
                logger.info(
                    "Orchestrazione completata (risposta diretta)",
                    rounds=round_num + 1,
                    tool_calls_total=len(tool_calls_made),
                )
                return {
                    "ok": True,
                    "message": assistant_msg,
                    "model": response.get("model", ""),
                    "tool_calls_made": tool_calls_made,
                    "rounds": round_num + 1,
                }

            # 2026-04-02 22:29 - Esegui ogni tool richiesto
            # Prima aggiungi il messaggio dell'assistente alla conversazione
            conversation.append(assistant_msg)

            for tc in tool_calls:
                tool_name = tc.get("function", {}).get("name", "")
                tool_args = tc.get("function", {}).get("arguments", {})

                logger.info(
                    "Tool call richiesta dal modello",
                    round_num=round_num,
                    tool_name=tool_name,
                    arg_keys=list(tool_args.keys()) if isinstance(tool_args, dict) else [],
                )

                # 2026-04-02 22:29 - Esegui il tool tramite il registry
                tool_result = self.registry.execute_tool(tool_name, tool_args)

                tool_calls_made.append({
                    "round": round_num,
                    "tool_name": tool_name,
                    "arguments": tool_args,
                    "ok": tool_result.get("ok", False),
                })

                # 2026-04-02 22:29 - Aggiungi il risultato alla conversazione come messaggio "tool"
                # Formato Ollama: {"role": "tool", "content": "..."}
                tool_content = json.dumps(tool_result, ensure_ascii=False, default=str)
                conversation.append({
                    "role": "tool",
                    "content": tool_content,
                })

            # 2026-04-02 22:29 - Verifica limite round
            if round_num >= self.max_tool_rounds:
                logger.warning(
                    "Limite massimo tool rounds raggiunto",
                    max_rounds=self.max_tool_rounds,
                    tool_calls_total=len(tool_calls_made),
                )
                return {
                    "ok": True,
                    "message": assistant_msg,
                    "model": response.get("model", ""),
                    "tool_calls_made": tool_calls_made,
                    "rounds": round_num + 1,
                    "warning": f"Limite massimo di {self.max_tool_rounds} tool rounds raggiunto",
                }

        # 2026-04-02 22:29 - Fallback (non dovrebbe arrivarci)
        return {
            "ok": False,
            "message": {},
            "model": "",
            "tool_calls_made": tool_calls_made,
            "rounds": self.max_tool_rounds,
            "error": {"error_type": "MAX_ROUNDS", "message": "Ciclo interrotto"},
        }
