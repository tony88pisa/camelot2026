# src/ai_trader/core/ollama_client.py
# 2026-04-02 21:06 - Adapter unico per Ollama (client HTTP)
# Usa la configurazione centralizzata e il logger JSONL
"""
OllamaClient  adapter HTTP per comunicare con il server Ollama locale.

Funzionalit:
- chat(): chiama /api/chat con supporto a tools/function calling
- health_check(): verifica che il server risponda
- Logging strutturato JSONL (solo meta-info, no contenuti messaggi)
- Retry singolo su errori di rete temporanei
- Gestione errori strutturata
"""

import json
import time
import urllib.error
import urllib.request
from typing import Any

from ai_trader.config.settings import get_settings
from ai_trader.logging.jsonl_logger import get_logger

# 2026-04-02 21:06 - Logger per questo modulo
logger = get_logger("ollama_client")


# ==============================================================================
# Error helper  2026-04-02 21:06
# ==============================================================================
def format_ollama_error(error: Exception, context: str = "") -> dict[str, Any]:
    """
    Converte un'eccezione in un messaggio strutturato per il sistema.
    Non espone stacktrace ma solo info utili.
    # 2026-04-02 21:06 - Creazione helper errori
    """
    error_type = type(error).__name__

    if isinstance(error, urllib.error.URLError):
        if hasattr(error, "reason"):
            reason = str(error.reason)
            if "Connection refused" in reason or "No connection" in reason:
                return {
                    "error_type": "CONNECTION_REFUSED",
                    "message": "Ollama server non raggiungibile",
                    "detail": reason,
                    "context": context,
                    "suggestion": "Verifica che Ollama sia in esecuzione (ollama serve)",
                }
            if "timed out" in reason.lower():
                return {
                    "error_type": "TIMEOUT",
                    "message": "Timeout connessione Ollama",
                    "detail": reason,
                    "context": context,
                    "suggestion": "Il server potrebbe essere sovraccarico",
                }
        return {
            "error_type": "NETWORK_ERROR",
            "message": f"Errore di rete: {error}",
            "detail": str(error),
            "context": context,
        }

    if isinstance(error, urllib.error.HTTPError):
        return {
            "error_type": "HTTP_ERROR",
            "message": f"HTTP {error.code}: {error.reason}",
            "detail": str(error),
            "context": context,
        }

    if isinstance(error, TimeoutError):
        return {
            "error_type": "TIMEOUT",
            "message": "Timeout durante la richiesta",
            "detail": str(error),
            "context": context,
        }

    if isinstance(error, json.JSONDecodeError):
        return {
            "error_type": "PARSE_ERROR",
            "message": "Risposta Ollama non JSON valida",
            "detail": str(error),
            "context": context,
        }

    return {
        "error_type": error_type,
        "message": str(error),
        "detail": "",
        "context": context,
    }


# ==============================================================================
# OllamaClient  2026-04-02 21:06
# ==============================================================================
class OllamaClient:
    """
    Client HTTP per comunicare con Ollama locale.
    Usa urllib (stdlib)  nessuna dipendenza esterna.

    # 2026-04-02 21:06 - Creazione classe OllamaClient
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        """
        Inizializza il client Ollama.
        Se i parametri non sono forniti, li legge dalla configurazione centralizzata.
        # 2026-04-02 21:06

        Args:
            host: hostname del server Ollama (default: da .env/settings)
            port: porta del server Ollama (default: da .env/settings)
            model: modello LLM da usare (default: da .env/settings)
            timeout: timeout in secondi per le richieste HTTP
        """
        settings = get_settings()

        self.host = host or settings.OLLAMA_HOST
        self.port = port or settings.OLLAMA_PORT
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout or settings.OLLAMA_TIMEOUT
        self.base_url = f"http://{self.host}:{self.port}"

        logger.info(
            "OllamaClient inizializzato",
            host=self.host,
            port=self.port,
            model=self.model,
            timeout=self.timeout,
        )

    # --------------------------------------------------------------------------
    # health_check  2026-04-02 21:06
    # --------------------------------------------------------------------------
    def health_check(self) -> bool:
        """
        Verifica che il server Ollama sia raggiungibile.
        Chiama GET /api/tags (endpoint leggero).
        Restituisce True se il server risponde con HTTP 200.
        # 2026-04-02 21:06

        Returns:
            True se Ollama risponde, False altrimenti
        """
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    logger.info("health_check OK", url=url)
                    return True
                # 2026-04-02 21:06 - Status non 200 inatteso
                logger.warning("health_check status inatteso", status=resp.status)
                return False
        except Exception as e:
            err_info = format_ollama_error(e, context="health_check")
            # 2026-04-02 21:15 - Fix: rinominato message -> error_msg per evitare conflitto
            logger.warning(
                "health_check FAIL",
                error_type=err_info["error_type"],
                error_msg=err_info["message"],
            )
            return False

    # --------------------------------------------------------------------------
    # chat  2026-04-02 21:06
    # --------------------------------------------------------------------------
    def chat(
        self,
        messages: list[dict],
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        timeout: int | None = None,
        num_ctx: int | None = 4096,
    ) -> dict[str, Any]:
        """
        Chiama l'endpoint /api/chat di Ollama.
        # 2026-04-02 21:06

        Args:
            messages: lista di messaggi [{"role": "user", "content": "..."}]
            temperature: temperatura di sampling (opzionale)
            max_tokens: numero massimo di token in risposta (opzionale)
            tools: lista di tool definitions per function calling (opzionale)

        Returns:
            dict con chiavi:
                - "ok": bool
                - "message": dict con la risposta (role, content) se ok
                - "model": str modello usato
                - "duration_ms": int durata in millisecondi
                - "error": dict errore strutturato se non ok
        """
        url = f"{self.base_url}/api/chat"

        # 2026-04-02 21:06 - Costruzione payload
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        # Opzioni facoltative
        options: dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if num_ctx is not None:
            options["num_ctx"] = num_ctx
        if options:
            payload["options"] = options

        if tools is not None:
            payload["tools"] = tools

        # 2026-04-02 21:06 - Log meta-info (NO contenuto messaggi)
        logger.info(
            "chat request",
            model=self.model,
            message_count=len(messages),
            has_tools=tools is not None,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # 2026-04-13 13:48 - v10.4.1 Resiliency Upgrade: Incremental Retries
        last_error: Exception | None = None
        for attempt in range(4):  # max 3 retries (v10.4.1 stability)
            start_time = time.monotonic()
            current_timeout = timeout or self.timeout
            try:
                result = self._do_chat_request(url, payload, timeout=current_timeout)
                duration_ms = int((time.monotonic() - start_time) * 1000)

                # 2026-04-02 21:06 - Log successo (solo meta-info)
                response_content = result.get("message", {}).get("content", "")
                logger.info(
                    "chat response OK",
                    model=result.get("model", self.model),
                    duration_ms=duration_ms,
                    response_length=len(response_content),
                    eval_count=result.get("eval_count"),
                )

                return {
                    "ok": True,
                    "message": result.get("message", {}),
                    "model": result.get("model", self.model),
                    "duration_ms": duration_ms,
                    "eval_count": result.get("eval_count"),
                    "total_duration": result.get("total_duration"),
                }

            except (urllib.error.URLError, TimeoutError, OSError) as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                last_error = e

                if attempt == 0:
                    # 2026-04-02 21:06 - Primo tentativo fallito, retry
                    logger.warning(
                        "chat request failed, retry in corso",
                        attempt=attempt + 1,
                        error=str(e),
                        duration_ms=duration_ms,
                    )
                    # Backoff esponenziale semplice: 2s, 4s, 8s
                    time.sleep(2 * (attempt + 1))
                    continue
                else:
                    # 2026-04-02 21:06 - Anche il retry ha fallito
                    err_info = format_ollama_error(e, context="chat")
                    # 2026-04-02 21:15 - Fix: rinominato message -> error_msg
                    logger.error(
                        "chat request FAILED after retry",
                        error_type=err_info["error_type"],
                        error_msg=err_info["message"],
                        duration_ms=duration_ms,
                    )
                    return {
                        "ok": False,
                        "message": {},
                        "model": self.model,
                        "duration_ms": duration_ms,
                        "error": err_info,
                    }

            except json.JSONDecodeError as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                err_info = format_ollama_error(e, context="chat")
                logger.error(
                    "chat response parse error",
                    error_type=err_info["error_type"],
                    duration_ms=duration_ms,
                )
                return {
                    "ok": False,
                    "message": {},
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "error": err_info,
                }

            except Exception as e:
                duration_ms = int((time.monotonic() - start_time) * 1000)
                err_info = format_ollama_error(e, context="chat")
                # 2026-04-02 21:15 - Fix: rinominato message -> error_msg
                logger.error(
                    "chat unexpected error",
                    error_type=err_info["error_type"],
                    error_msg=err_info["message"],
                    duration_ms=duration_ms,
                )
                return {
                    "ok": False,
                    "message": {},
                    "model": self.model,
                    "duration_ms": duration_ms,
                    "error": err_info,
                }

        # 2026-04-02 21:06 - Fallback (non dovrebbe arrivarci)
        err_info = format_ollama_error(
            last_error or RuntimeError("Unknown error"), context="chat"
        )
        return {
            "ok": False,
            "message": {},
            "model": self.model,
            "duration_ms": 0,
            "error": err_info,
        }

    # --------------------------------------------------------------------------
    # _do_chat_request (internal)  2026-04-02 21:06
    # --------------------------------------------------------------------------
    def _do_chat_request(self, url: str, payload: dict, timeout: int | None = None) -> dict:
        """
        Esegue la richiesta HTTP POST a Ollama /api/chat.
        Metodo interno separato per facilitare il testing.
        # 2026-04-02 21:06

        Args:
            url: URL completo dell'endpoint
            payload: body della richiesta

        Returns:
            dict con la risposta JSON di Ollama

        Raises:
            urllib.error.URLError: errore di rete
            urllib.error.HTTPError: errore HTTP (status != 200)
            json.JSONDecodeError: risposta non JSON
            TimeoutError: timeout
        """
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # Usa il timeout passato o quello di default dell'istanza
        with urllib.request.urlopen(req, timeout=timeout or self.timeout) as resp:
            if resp.status != 200:
                raise urllib.error.HTTPError(
                    url, resp.status, f"Status {resp.status}", resp.headers, resp
                )
            body = resp.read().decode("utf-8")
            return json.loads(body)
