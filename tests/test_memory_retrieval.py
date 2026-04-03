# tests/test_memory_retrieval.py
# 2026-04-02 23:45 - Test suite per il modulo Memory Retrieval
import pytest

from datetime import datetime, timezone
from pathlib import Path

from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.memory.retrieval import MemoryRetrieval


@pytest.fixture
def memory_retrieval_isolated(tmp_path):
    """
    Fixture isolata per la search.
    # 2026-04-02 23:45
    """
    ep_dir = tmp_path / "episodes"
    les_dir = tmp_path / "lessons"

    episodes = EpisodeStore(base_dir=ep_dir)
    lessons = LessonStore(base_dir=les_dir)
    retrieval = MemoryRetrieval(base_dir=tmp_path, episodes=episodes, lessons=lessons)
    
    return {
        "ret": retrieval,
        "episodes": episodes,
        "lessons": lessons,
    }


class TestMemoryRetrieval:

    def test_search_episodes_by_text(self, memory_retrieval_isolated):
        """Testa la ricerca di episodes per fulltext."""
        ret = memory_retrieval_isolated["ret"]
        eps = memory_retrieval_isolated["episodes"]
        
        eps.append_episode("trading", "buy_attempt", {"status": "failed", "error": "insufficient funds"})
        eps.append_episode("trading", "buy_attempt", {"status": "success", "error": "none"})
        
        res = ret.search_episodes(query="insufficient funds")
        assert res.total_hits == 1
        assert "insufficient funds" in res.hits[0].excerpt

    def test_search_episodes_by_kind(self, memory_retrieval_isolated):
        """Testa la ricerca esatta per kind."""
        ret = memory_retrieval_isolated["ret"]
        eps = memory_retrieval_isolated["episodes"]
        
        eps.append_episode("research", "market_scan", {"price": 10})
        eps.append_episode("research", "news_scan", {"headline": "Bitcoin!"})
        
        res = ret.search_episodes(kind="news_scan")
        assert res.total_hits == 1
        assert res.hits[0].kind == "news_scan"
        assert res.hits[0].score > 0

    def test_search_episodes_by_tag(self, memory_retrieval_isolated):
        """Testa il forte bonus di punteggio assegnato ai tag esatti."""
        ret = memory_retrieval_isolated["ret"]
        eps = memory_retrieval_isolated["episodes"]
        
        eps.append_episode("system", "ping", {}, tags=["network"])
        
        res = ret.search_episodes(tags=["network"])
        assert res.total_hits == 1
        # Il tag match esalto assegna almeno 30
        assert res.hits[0].score >= 30.0

    def test_search_lessons(self, memory_retrieval_isolated):
        """Testa la ricerca su markdown malformato/ben formattato sulle lessons."""
        ret = memory_retrieval_isolated["ret"]
        les = memory_retrieval_isolated["lessons"]
        
        les.append_lesson("trading", "Avoiding bad entries", "Do not trade on Friday if volatility is low.", tags=["volatility"])
        res = ret.search_lessons(query="volatility")
        
        assert res.total_hits == 1
        # Query match content (15), tag match bonus possible
        assert res.hits[0].title == "Avoiding bad entries"
        assert "volatility" in res.hits[0].tags

    def test_search_all(self, memory_retrieval_isolated):
        """Testa la logica aggregata di query tra multiple source_type."""
        ret = memory_retrieval_isolated["ret"]
        eps = memory_retrieval_isolated["episodes"]
        les = memory_retrieval_isolated["lessons"]
        
        eps.append_episode("trading", "buy", {"error": "connection timeout"})
        les.append_lesson("system", "Network Reliability", "Sometimes we get a connection timeout.")
        
        res = ret.search_all(query="timeout")
        assert res.total_hits == 2
        
        source_types = [h.source_type for h in res.hits]
        assert "episode" in source_types
        assert "lesson" in source_types

    def test_build_memory_context_empty(self, memory_retrieval_isolated):
        """Se vuoto, il dictionary restituito deve essere formattato correttamente ma vuoto."""
        ret = memory_retrieval_isolated["ret"]
        
        ctx = ret.build_memory_context("hacker_attack")
        assert ctx["total_hits"] == 0
        assert "Nessun hit storico trovato" in ctx["summary"]
        assert len(ctx["top_lessons"]) == 0
        assert len(ctx["top_episodes"]) == 0

    def test_build_memory_context_with_results(self, memory_retrieval_isolated):
        """Testa la validità logica del context builder sintetico."""
        ret = memory_retrieval_isolated["ret"]
        eps = memory_retrieval_isolated["episodes"]
        les = memory_retrieval_isolated["lessons"]
        
        eps.append_episode("trading", "test", {"msg": "foo"})
        les.append_lesson("trading", "Foo pattern", "the foo is strong")
        
        ctx = ret.build_memory_context("foo")
        assert ctx["total_hits"] == 2
        assert "Trovate 1 lesson rilevanti e 1 episodi collegati" in ctx["summary"]
        assert ctx["top_lessons"][0]["title"] == "Foo pattern"
