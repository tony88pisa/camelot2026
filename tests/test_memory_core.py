# tests/test_memory_core.py
# 2026-04-02 23:09 - Test suite per il modulo Memory Core
# Copre: EpisodeStore, LessonStore, MemoryIndex e le API wrapper
"""
Test suite per src/ai_trader/memory/

Copre:
- Creazione strutture cartelle corrette
- Scrittura/lettura episodi in category (trading, research, system)
- Scrittura/lettura lessons in category (trading, system) e formato MD
- Rigenerazione indice MEMORY.md
"""

from datetime import datetime
from pathlib import Path

import pytest

from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.memory.memory_index import MemoryIndex


@pytest.fixture
def memory_stores(tmp_path):
    """
    Fixture che isola la memoria in una directory temporanea.
    Evita di scrivere nel memdir reale del progetto.
    # 2026-04-02 23:09
    """
    episodes_dir = tmp_path / "episodes"
    lessons_dir = tmp_path / "lessons"
    index_dir = tmp_path / "index"
    
    episodes = EpisodeStore(base_dir=episodes_dir)
    lessons = LessonStore(base_dir=lessons_dir)
    m_index = MemoryIndex(base_dir=index_dir)
    # Patch manuale degli store per index_builder in mode test
    m_index.episodes = episodes
    m_index.lessons = lessons
    
    return {
        "episodes": episodes,
        "lessons": lessons,
        "index": m_index,
        "base": tmp_path
    }


# ==============================================================================
# TEST: EpisodeStore — 2026-04-02 23:09
# ==============================================================================
class TestEpisodeStore:

    def test_dir_creation(self, memory_stores):
        """Le dir di categoria vengono create in init."""
        episodes_dir = memory_stores["base"] / "episodes"
        assert episodes_dir.exists()
        assert (episodes_dir / "trading").exists()
        assert (episodes_dir / "research").exists()
        assert (episodes_dir / "system").exists()

    def test_append_episode(self, memory_stores):
        """append_episode scrive e crea l'ID."""
        store = memory_stores["episodes"]
        ep_id = store.append_episode(
            category="trading",
            kind="test_event",
            payload={"price": 100},
            tags=["btc"]
        )
        assert isinstance(ep_id, str)
        assert len(ep_id) > 10

    def test_load_episodes(self, memory_stores):
        """load_episodes legge i dati salvati loggati oggi."""
        store = memory_stores["episodes"]
        store.append_episode(category="research", kind="a", payload={})
        store.append_episode(category="research", kind="b", payload={})
        
        results = store.load_episodes("research")
        assert len(results) == 2
        assert results[0]["kind"] == "a"
        assert results[1]["kind"] == "b"

    def test_load_episodes_invalid_category(self, memory_stores):
        """Lettura da categoria vuota o inesistente ritorna lista vuota."""
        store = memory_stores["episodes"]
        assert store.load_episodes("unknown_cat") == []


# ==============================================================================
# TEST: LessonStore (Markdown) — 2026-04-02 23:09
# ==============================================================================
class TestLessonStore:

    def test_append_lesson_markdown(self, memory_stores):
        """append_lesson crea un file markdown strutturato."""
        store = memory_stores["lessons"]
        filename = store.append_lesson(
            category="trading",
            title="My Test Lesson",
            content="This is the content of the lesson.",
            tags=["important", "test"]
        )
        
        assert filename.endswith(".md")
        file_path = memory_stores["base"] / "lessons" / "trading" / filename
        assert file_path.exists()
        
        content = file_path.read_text("utf-8")
        assert "My Test Lesson" in content
        assert "This is the content of the lesson." in content
        assert "category: trading" in content
        assert "important, test" in content

    def test_read_lessons(self, memory_stores):
        """read_lessons legge i metadata dai file MD creati."""
        store = memory_stores["lessons"]
        store.append_lesson(category="system", title="Lesson A", content="A")
        store.append_lesson(category="system", title="Lesson B", content="B")
        
        lessons = store.read_lessons("system")
        assert len(lessons) == 2
        titles = [l["title"] for l in lessons]
        assert "Lesson A" in titles
        assert "Lesson B" in titles
        

# ==============================================================================
# TEST: MemoryIndex — 2026-04-02 23:09
# ==============================================================================
class TestMemoryIndex:

    def test_update_memory_index(self, memory_stores):
        """update_memory_index genera il MEMORY.md."""
        eps = memory_stores["episodes"]
        les = memory_stores["lessons"]
        idx = memory_stores["index"]
        
        # Inserisci dati
        eps.append_episode("trading", "buy_order", {"amount": 1})
        eps.append_episode("trading", "buy_order", {"amount": 2})
        les.append_lesson("trading", "Avoid bad trades", "Wait for trend.")
        
        # Aggiorna index
        idx.update_memory_index()
        
        index_file = memory_stores["base"] / "index" / "MEMORY.md"
        assert index_file.exists()
        
        content = index_file.read_text("utf-8")
        assert "AI Trader Memory Index" in content
        assert "Avoid bad trades" in content
        assert "buy_order: 2 eventi" in content  # Raggruppa per kind
