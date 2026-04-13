import os
import json
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from ai_trader.risk.risk_state_tracker import RiskStateTracker
from ai_trader.memory.lesson_store import LessonStore

@pytest.fixture
def temp_memdir(tmp_path):
    """Crea una directory temporanea per le lezioni."""
    d = tmp_path / "memdir"
    d.mkdir()
    (d / "lessons").mkdir()
    return d

@pytest.fixture
def lesson_store(temp_memdir):
    # Mocking MCP per evitare connessioni di rete nei test
    with patch("ai_trader.memory.lesson_store.McpSseHandler"):
        return LessonStore(base_dir=temp_memdir / "lessons")

@pytest.fixture
def tracker(lesson_store):
    return RiskStateTracker(lesson_store=lesson_store)

class TestRiskPersistence:

    def test_emit_incident_lesson_content(self, tracker, temp_memdir):
        """Verifica che la lezione emessa contenga il JSON strutturato."""
        # Setup stato
        tracker.consecutive_errors = 5
        tracker.system_cooldown_until = time.time() + 3600
        tracker.last_risk_block_reason = "UNIT_TEST_REASON"
        
        # Emissione
        tracker.emit_incident_lesson("Test Incident", "TEST_TYPE", "warning")
        
        # Verifica file creato
        system_dir = temp_memdir / "lessons" / "system"
        files = list(system_dir.glob("*.md"))
        assert len(files) == 1
        
        content = files[0].read_text(encoding="utf-8")
        assert "```json" in content
        assert '"incident_type": "TEST_TYPE"' in content
        assert '"consecutive_errors": 5' in content
        assert '"UNIT_TEST_REASON"' in content

    def test_restore_state_from_valid_lesson(self, tracker, lesson_store):
        """Verifica il ripristino dello stato da una lezione strutturata recente."""
        # 1. Creiamo una lezione strutturata a mano nel LessonStore
        cooldown_target = time.time() + 1800 # 30 min da ora
        incident_data = {
            "version": "1.0",
            "incident_type": "CRITICAL_ERROR",
            "occurred_at": time.time() - 60, # 1 minuto fa
            "consecutive_errors": 3,
            "system_cooldown_until": cooldown_target
        }
        
        content = f"## payload\n```json\n{json.dumps(incident_data)}\n```"
        lesson_store.append_lesson("system", "Prev Incident", content)
        
        # 2. Creiamo un nuovo tracker e chiediamo il restore
        new_tracker = RiskStateTracker(lesson_store=lesson_store)
        new_tracker.restore_recent_incident_state(lookback_seconds=3600)
        
        # 3. Verifiche
        assert new_tracker.consecutive_errors == 3
        assert abs(new_tracker.system_cooldown_until - cooldown_target) < 1.0

    def test_restore_ignore_old_lesson(self, tracker, lesson_store):
        """Verifica che le lezioni troppo vecchie vengano ignorate."""
        incident_data = {
            "version": "1.0",
            "incident_type": "OLD_ERROR",
            "occurred_at": time.time() - 20000, # ~5 ore fa
            "consecutive_errors": 10
        }
        content = f"```json\n{json.dumps(incident_data)}\n```"
        lesson_store.append_lesson("system", "Old Incident", content)
        
        new_tracker = RiskStateTracker(lesson_store=lesson_store)
        new_tracker.restore_recent_incident_state(lookback_seconds=14400) # 4 ore lookback
        
        # Deve rimanere a zero
        assert new_tracker.consecutive_errors == 0

    def test_restore_ignore_unstructured_lesson(self, tracker, lesson_store):
        """Verifica che le lezioni senza JSON non attivino il restore."""
        lesson_store.append_lesson("system", "Prose Lesson", "This is just text without json block.")
        
        new_tracker = RiskStateTracker(lesson_store=lesson_store)
        new_tracker.restore_recent_incident_state()
        
        assert new_tracker.consecutive_errors == 0
