# tests/test_read_only_tools.py
# 2026-04-03 00:55 - Test suite per i tools Read-Only
"""
Suite isolata che testa execution e compliance dei tools senza
chiamare la rete ne sporcare il db di memoria.
"""

import pytest

from ai_trader.mcp.registry import ToolRegistry
from ai_trader.memory.retrieval import MemoryRetrieval
from ai_trader.tools.read_only_tools import (
    GetSystemTimeTool,
    GetMemoryContextTool,
    GetRecentEpisodesTool,
    GetRecentLessonsTool,
    GetMarketSnapshotStubTool,
)

@pytest.fixture
def ro_tools_isolated(tmp_path):
    """
    Istanzia retrieval e tool su tmp_path
    # 2026-04-03 00:55
    """
    retrieval = MemoryRetrieval(base_dir=tmp_path)
    
    # Popolo dati mock base per i test che ne dipendono (lessons & episodes)
    retrieval.episodes.append_episode("trading", "test_kind", {"val": 123}, tags=["foo"])
    retrieval.lessons.append_lesson("trading", "Test Lesson", "body test")

    registry = ToolRegistry()
    registry.register(GetSystemTimeTool())
    registry.register(GetMemoryContextTool(retrieval=retrieval))
    registry.register(GetRecentEpisodesTool(retrieval=retrieval))
    registry.register(GetRecentLessonsTool(retrieval=retrieval))
    registry.register(GetMarketSnapshotStubTool())

    return {
        "registry": registry,
        "retrieval": retrieval
    }

class TestReadOnlyTools:

    def test_get_system_time(self, ro_tools_isolated):
        registry = ro_tools_isolated["registry"]
        res = registry.execute_tool("get_system_time", {})
        
        assert res["ok"] is True
        assert "isoformat" in res["result"]
        assert res["result"]["timezone"] == "UTC"

    def test_get_memory_context(self, ro_tools_isolated):
        registry = ro_tools_isolated["registry"]
        res = registry.execute_tool("get_memory_context", {"query": "foo", "category": "trading"})
        
        assert res["ok"] is True
        ctx = res["result"]
        assert ctx["total_hits"] >= 1
        assert "foo" in ctx["summary"]

    def test_get_recent_trading_episodes(self, ro_tools_isolated):
        registry = ro_tools_isolated["registry"]
        res = registry.execute_tool("get_recent_trading_episodes", {"limit": 5})

        assert res["ok"] is True
        body = res["result"]
        assert len(body) >= 1
        assert body[0]["kind"] == "test_kind"

    def test_get_recent_lessons(self, ro_tools_isolated):
        registry = ro_tools_isolated["registry"]
        res = registry.execute_tool("get_recent_lessons", {"category": "trading", "limit": 2})

        assert res["ok"] is True
        body = res["result"]
        assert len(body) >= 1
        assert body[0]["title"] == "Test Lesson"

    def test_get_market_snapshot_stub(self, ro_tools_isolated):
        registry = ro_tools_isolated["registry"]
        res = registry.execute_tool("get_market_snapshot_stub", {"symbol": "BTC/USDT"})

        assert res["ok"] is True
        body = res["result"]
        assert body["status"] == "stub"
        assert body["source"] == "stub_memory_layer"
        assert body["symbol"] == "BTC/USDT"
        assert body["price"] == 98500.00
