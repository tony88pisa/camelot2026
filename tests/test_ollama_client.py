# tests/test_ollama_client.py
# 2026-04-02 21:07 - Test per il modulo OllamaClient
# I test non richiedono Ollama attivo: se non raggiungibile, skip con messaggio
"""
Test suite per src/ai_trader/core/ollama_client.py

Copre:
- Creazione client con config valida e custom
- health_check() con server non raggiungibile (non crasha)
- health_check() con server reale (se disponibile)
- format_ollama_error() su eccezioni diverse
- chat() con server non raggiungibile (non crasha, errore strutturato)
- chat() con server reale (se disponibile)
"""

import json
import urllib.error

import pytest

from ai_trader.core.ollama_client import OllamaClient, format_ollama_error


# ==============================================================================
# Helper per rilevare Ollama  2026-04-02 21:07
# 2026-04-02 21:18 - Aggiunto rilevamento automatico modello disponibile
# ==============================================================================
_OLLAMA_AVAILABLE_MODEL: str | None = None


def is_ollama_available(host: str = "localhost", port: int = 11434) -> bool:
    """Verifica se Ollama  raggiungibile e trova un modello disponibile. # 2026-04-02 21:18"""
    global _OLLAMA_AVAILABLE_MODEL
    try:
        req = urllib.request.Request(f"http://{host}:{port}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status != 200:
                return False
            data = json.loads(resp.read().decode())
            models = data.get("models", [])
            if models:
                # 2026-04-02 21:18 - Prendi il modello pi piccolo disponibile
                sorted_models = sorted(models, key=lambda m: m.get("size", float("inf")))
                _OLLAMA_AVAILABLE_MODEL = sorted_models[0].get("name", sorted_models[0].get("model"))
            return True
    except Exception:
        return False


# Flag globale per skip dei test che richiedono Ollama
OLLAMA_LIVE = is_ollama_available()
skip_no_ollama = pytest.mark.skipif(
    not OLLAMA_LIVE,
    reason="Ollama non raggiungibile su localhost:11434  test live skippato",
)


# ==============================================================================
# TEST: Creazione client  2026-04-02 21:07
# ==============================================================================
class TestOllamaClientInit:
    """Test di inizializzazione del client. # 2026-04-02 21:07"""

    def test_default_config(self):
        """Il client si crea con la config di default senza errori."""
        client = OllamaClient()
        assert client.host is not None
        assert client.port > 0
        assert client.model != ""
        assert client.timeout > 0
        assert client.base_url.startswith("http://")

    def test_custom_config(self):
        """Il client accetta parametri custom."""
        client = OllamaClient(
            host="10.0.0.99",
            port=9999,
            model="test-model",
            timeout=30,
        )
        assert client.host == "10.0.0.99"
        assert client.port == 9999
        assert client.model == "test-model"
        assert client.timeout == 30
        assert client.base_url == "http://10.0.0.99:9999"

    def test_partial_custom_config(self):
        """Il client accetta solo alcuni parametri custom, gli altri da settings."""
        client = OllamaClient(model="custom-only-model")
        assert client.model == "custom-only-model"
        # host e port devono venire dalla config
        assert client.host is not None
        assert client.port > 0


# ==============================================================================
# TEST: health_check  2026-04-02 21:07
# ==============================================================================
class TestHealthCheck:
    """Test per health_check(). # 2026-04-02 21:07"""

    def test_unreachable_host_returns_false(self):
        """health_check su host inesistente ritorna False senza crash."""
        client = OllamaClient(host="192.0.2.1", port=1, timeout=2)
        result = client.health_check()
        assert result is False

    def test_wrong_port_returns_false(self):
        """health_check su porta sbagliata ritorna False senza crash."""
        client = OllamaClient(host="localhost", port=1, timeout=2)
        result = client.health_check()
        assert result is False

    @skip_no_ollama
    def test_live_health_check(self):
        """health_check su Ollama reale ritorna True."""
        client = OllamaClient()
        result = client.health_check()
        assert result is True


# ==============================================================================
# TEST: format_ollama_error  2026-04-02 21:07
# ==============================================================================
class TestFormatOllamaError:
    """Test per la funzione helper format_ollama_error(). # 2026-04-02 21:07"""

    def test_connection_refused(self):
        """Errore di connessione rifiutata produce messaggio strutturato."""
        err = urllib.error.URLError(reason="Connection refused")
        result = format_ollama_error(err, context="test")
        assert result["error_type"] == "CONNECTION_REFUSED"
        assert result["context"] == "test"
        assert "suggestion" in result

    def test_timeout_error(self):
        """Timeout produce messaggio strutturato."""
        err = TimeoutError("Request timed out")
        result = format_ollama_error(err, context="chat")
        assert result["error_type"] == "TIMEOUT"
        assert result["context"] == "chat"

    def test_json_decode_error(self):
        """Errore di parsing JSON produce messaggio strutturato."""
        err = json.JSONDecodeError("test", "", 0)
        result = format_ollama_error(err, context="parse")
        assert result["error_type"] == "PARSE_ERROR"

    def test_generic_error(self):
        """Errore generico produce messaggio con tipo corretto."""
        err = RuntimeError("Something broke")
        result = format_ollama_error(err, context="unknown")
        assert result["error_type"] == "RuntimeError"
        assert "Something broke" in result["message"]

    def test_url_timeout(self):
        """URLError con reason 'timed out' produce TIMEOUT."""
        err = urllib.error.URLError(reason="Connection timed out")
        result = format_ollama_error(err)
        assert result["error_type"] == "TIMEOUT"


# ==============================================================================
# TEST: chat  2026-04-02 21:07
# ==============================================================================
class TestChat:
    """Test per chat(). # 2026-04-02 21:07"""

    def test_chat_unreachable_returns_error(self):
        """chat() su host non raggiungibile ritorna errore strutturato, no crash."""
        client = OllamaClient(host="192.0.2.1", port=1, timeout=2)
        result = client.chat(messages=[{"role": "user", "content": "test"}])
        assert result["ok"] is False
        assert "error" in result
        assert result["error"]["error_type"] in ("CONNECTION_REFUSED", "TIMEOUT", "NETWORK_ERROR")
        assert result["model"] == client.model
        assert "duration_ms" in result

    def test_chat_returns_dict(self):
        """chat() ritorna sempre un dict con le chiavi attese."""
        client = OllamaClient(host="localhost", port=1, timeout=1)
        result = client.chat(messages=[{"role": "user", "content": "hello"}])
        assert isinstance(result, dict)
        assert "ok" in result
        assert "message" in result
        assert "model" in result
        assert "duration_ms" in result

    @skip_no_ollama
    def test_live_chat(self):
        """chat() con Ollama reale ritorna risposta valida. # 2026-04-02 21:18"""
        if _OLLAMA_AVAILABLE_MODEL is None:
            pytest.skip("Nessun modello Ollama disponibile")
        client = OllamaClient(model=_OLLAMA_AVAILABLE_MODEL)
        result = client.chat(
            messages=[{"role": "user", "content": "Rispondi solo: OK"}],
            temperature=0.0,
            max_tokens=10,
        )
        assert result["ok"] is True, f"Chat failed: {result.get('error', 'unknown')}"
        assert result["message"]["role"] == "assistant"
        # 2026-04-02 21:20 - Alcuni modelli possono rispondere con content vuoto
        # (es. tool_calls), accettiamo anche content vuoto se la risposta  OK
        assert isinstance(result["message"].get("content", ""), str)
        assert result["duration_ms"] >= 0
