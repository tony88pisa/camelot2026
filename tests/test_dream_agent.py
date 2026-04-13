# tests/test_dream_agent.py
# 2026-04-02 23:15 - Test suite per il modulo Dream Agent
"""
Test suite isolata per src/ai_trader/memory/dream_agent.py

Copre:
- Setup agent con memory isolata
- Effetto nessun episodio -> nessuna lesson
- Effetto ripetizioni -> creazione deterministica lesson
- Controlli su duplicati (niente double creation)
- Integrit ciclo (MEMORY.md viene aggiornato)
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone

from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.memory.memory_index import MemoryIndex
from ai_trader.memory.dream_agent import DreamAgent


@pytest.fixture
def dream_agent_isolated(tmp_path):
    """
    Fixture che isola il sistema di store in tmp_path.
    # 2026-04-02 23:15
    """
    ep_dir = tmp_path / "episodes"
    les_dir = tmp_path / "lessons"
    idx_dir = tmp_path / "index"
    
    episodes = EpisodeStore(base_dir=ep_dir)
    lessons = LessonStore(base_dir=les_dir)
    m_index = MemoryIndex(base_dir=idx_dir)
    
    agent = DreamAgent(episodes=episodes, lessons=lessons, memory_index=m_index)
    return {
        "agent": agent,
        "episodes": episodes,
        "lessons": lessons,
        "index": m_index,
        "base": tmp_path
    }


class TestDreamAgent:
    
    def test_run_empty_memory(self, dream_agent_isolated):
        """Zero episodi -> Zero lezioni, ma MEMORY.md viene generato."""
        agent = dream_agent_isolated["agent"]
        res = agent.run_dream_cycle(["trading", "system"])
        
        assert res["ok"] is True
        assert res["total_new_lessons"] == 0
        
        index_file = dream_agent_isolated["base"] / "index" / "MEMORY.md"
        assert index_file.exists()

    def test_frequent_pattern_detection(self, dream_agent_isolated):
        """Se ci sono 3 o pi episodi con lo stesso kind, crea una lesson."""
        agent = dream_agent_isolated["agent"]
        eps = dream_agent_isolated["episodes"]
        
        # Popolo 3 episodi identici
        for _ in range(3):
            eps.append_episode("system", "startup_check", payload={"status": "ok"})
            
        res = agent.run_dream_cycle(["system"])
        assert res["total_new_lessons"] == 1
        assert res["breakdown"]["system"] == 1
        
        # Verifico testualmente la lesson
        lessons = dream_agent_isolated["lessons"].read_lessons("system")
        assert len(lessons) == 1
        assert "frequency" in Path(lessons[0]['path']).read_text()
        assert "startup_check" in Path(lessons[0]['path']).read_text()

    def test_repeated_error_detection(self, dream_agent_isolated):
        """Se ci sono errori, crea error lesson."""
        agent = dream_agent_isolated["agent"]
        eps = dream_agent_isolated["episodes"]
        
        eps.append_episode("trading", "buy", payload={"ok": False, "error": "insufficient funds"})
        eps.append_episode("trading", "sell", payload={"error": "timeout"})
        eps.append_episode("trading", "scan", payload={"ok": True})
        
        res = agent.run_dream_cycle(["trading"])
        assert res["total_new_lessons"] == 1
        assert res["breakdown"]["trading"] == 1
        
    def test_anti_duplication(self, dream_agent_isolated):
        """Non deve creare una lezione per lo stesso pattern pi volte di seguito."""
        agent = dream_agent_isolated["agent"]
        eps = dream_agent_isolated["episodes"]
        
        # 3 eventi per far scattare la frequency rule
        for _ in range(3):
            eps.append_episode("research", "api_call", payload={})
            
        # Run 1 - crea la lesson
        res1 = agent.run_dream_cycle(["research"])
        assert res1["total_new_lessons"] == 1
        
        # Run 2 subitaneo con gli stessi dati (che ancora "esistono" dal loader)
        # Il detect deve ritrovarli, ma l'anti-duplication salta.
        res2 = agent.run_dream_cycle(["research"])
        assert res2["total_new_lessons"] == 0
