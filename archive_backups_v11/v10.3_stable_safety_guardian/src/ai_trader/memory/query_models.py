# src/ai_trader/memory/query_models.py
# 2026-04-02 23:45 - Modelli Dati per la Memory Retrieval
"""
Dataclasses per uniformare i risultati di ricerca tra Episode e Lesson.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryHit:
    """
    Rappresenta un singolo risultato (hit) proveniente dalla memoria.
    # 2026-04-02 23:45
    """
    source_type: str  # "episode", "lesson", "index"
    path: str
    score: float
    excerpt: str
    
    category: str | None = None
    timestamp: str | None = None
    title: str | None = None
    kind: str | None = None
    
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryQueryResult:
    """
    Contenitore per i risultati di una determinata query.
    # 2026-04-02 23:45
    """
    query: str
    total_hits: int
    hits: list[MemoryHit] = field(default_factory=list)
