# src/ai_trader/memory/retrieval.py
# 2026-04-02 23:45 - Memory Retrieval Engine
"""
Motore di ricerca (Query & Retrieval) per la Memoria pregressa (Episodes & Lessons).
Scoring testuale e deterministico. Nessuna dipendenza da LLM o VDB.
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.memory.query_models import MemoryHit, MemoryQueryResult

# 2026-04-02 23:45 - Logger
logger = get_logger("memory_retrieval")


class MemoryRetrieval:
    """
    Costruttore dell'engine di ricerca memoria deterministica.
    # 2026-04-02 23:45 
    """

    def __init__(
        self,
        base_dir: str | Path | None = None,
        episodes: EpisodeStore | None = None,
        lessons: LessonStore | None = None,
    ):
        """# 2026-04-02 23:45"""
        if base_dir:
            self.base_dir = Path(base_dir)
            self.episodes = episodes or EpisodeStore(self.base_dir / "episodes")
            self.lessons = lessons or LessonStore(self.base_dir / "lessons")
        else:
            from ai_trader.config.settings import get_settings
            self.base_dir = get_settings().MEMDIR
            self.episodes = episodes or EpisodeStore()
            self.lessons = lessons or LessonStore()

        logger.info("MemoryRetrieval inizializzato")

    def search_episodes(
        self,
        query: str | None = None,
        category: str | None = None,
        kind: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
        since: str | datetime | None = None,
        until: str | datetime | None = None,
    ) -> MemoryQueryResult:
        """
        API richiesta: Cerca episodi in base a criteri combinati testuali e tags.
        # 2026-04-02 23:45
        """
        cats_to_search = [category] if category else ["trading", "research", "system"]
        q_lower = query.lower() if query else None
        search_tags = set(tg.lower() for tg in tags) if tags else set()
        
        all_hits = []
        now = datetime.now(timezone.utc)

        for cat in cats_to_search:
            episodes = self.episodes.load_episodes(cat, since=since, until=until)
            for ep in episodes:
                score = 0.0
                
                # Check Kind
                ep_kind = ep.get("kind", "").lower()
                if kind and kind.lower() == ep_kind:
                    score += 20.0
                    
                # Check Tags
                ep_tags = [t.lower() for t in ep.get("tags", [])]
                ep_tags_set = set(ep_tags)
                if search_tags and search_tags.intersection(ep_tags_set):
                    score += 30.0 * len(search_tags.intersection(ep_tags_set))
                    
                # Fulltext Payload & Query
                ep_payload_str = json.dumps(ep.get("payload", {}), ensure_ascii=False).lower()
                if q_lower:
                    if q_lower in ep_kind:
                        score += 15.0
                    if any(q_lower in t for t in ep_tags):
                        score += 15.0
                    if q_lower in ep_payload_str:
                        score += 10.0
                        
                    # Se abbiamo una query testuale ma uno score 0, l'episodio non c'entra niente
                    if score == 0.0:
                        continue
                        
                # Considerazioni base su recency
                if score > 0:
                    try:
                        ep_time = datetime.fromisoformat(ep.get("timestamp", ""))
                        days_old = (now - ep_time).days
                        # Bonus piccolissimo logaritmico per episodi super recenti
                        bonus_recency = max(0, 5.0 - days_old)
                        score += bonus_recency
                    except Exception:
                        pass

                # Se nonostante filtri e recency lo score  <= 0 (o <= 0.5), scarta
                if score <= 0.5:
                    continue

                excerpt = ep_payload_str[:150] + ("..." if len(ep_payload_str) > 150 else "")
                
                hit = MemoryHit(
                    source_type="episode",
                    path=f"episode/{ep.get('id', 'unknown')}",
                    score=round(score, 2),
                    excerpt=excerpt,
                    category=cat,
                    timestamp=ep.get("timestamp"),
                    kind=ep.get("kind"),
                    tags=ep.get("tags", []),
                    metadata={"payload": ep.get("payload", {})}
                )
                all_hits.append(hit)

        all_hits.sort(key=lambda h: h.score, reverse=True)
        final_hits = all_hits[:limit]
        
        logger.info("Ricerca Episodi completata", query=query, category=category, found=len(final_hits))
        return MemoryQueryResult(query=query or "", total_hits=len(final_hits), hits=final_hits)

    def search_lessons(
        self,
        query: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> MemoryQueryResult:
        """
        API richiesta: Ricerca estesa e fulltext all'interno dei documenti Markdown delle lessons.
        Estrazione dei metadata manuale in caso di Markdown.
        # 2026-04-02 23:45
        """
        cats_to_search = [category] if category else ["trading", "system"]
        q_lower = query.lower() if query else None
        search_tags = set(tg.lower() for tg in tags) if tags else set()
        
        all_hits = []

        for cat in cats_to_search:
            cat_dir = self.lessons.base_dir / cat
            if not cat_dir.exists():
                continue
                
            for file_path in cat_dir.glob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning("Lesson script warning", file=file_path.name, err=str(e))
                    continue

                score = 0.0
                content_lower = content.lower()
                
                # Semplice heuristica extract title
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else file_path.stem
                
                # Heuristica extract timestamp e tags rudimentale
                ep_tags = []
                tags_match = re.search(r'tags:\s*\[(.*?)\]', content)
                if tags_match:
                    ep_tags = [t.strip().lower() for t in tags_match.group(1).split(",")]
                
                time_match = re.search(r'date:\s*([^\s]+)', content)
                timestamp = time_match.group(1).strip() if time_match else None

                ep_tags_set = set(ep_tags)
                
                # Criteri Scoring Lesson
                if search_tags and search_tags.intersection(ep_tags_set):
                    score += 30.0 * len(search_tags.intersection(ep_tags_set))
                    
                if q_lower:
                    if q_lower in title.lower():
                        score += 25.0
                    if any(q_lower in t for t in ep_tags):
                        score += 20.0
                    if q_lower in content_lower:
                        # Valore di frequenza interno
                        occurrences = content_lower.count(q_lower)
                        score += 15.0 + (occurrences * 0.5)  # bonus testuale leggero
                        
                    if score == 0.0:
                        continue

                # Qualifica
                if (query or tags) and score <= 0.0:
                    continue

                excerpt = " ".join(content.split()[:30]) + "..."
                
                hit = MemoryHit(
                    source_type="lesson",
                    path=str(file_path),
                    score=round(score, 2),
                    excerpt=excerpt,
                    category=cat,
                    timestamp=timestamp,
                    title=title,
                    tags=ep_tags,
                )
                all_hits.append(hit)

        all_hits.sort(key=lambda h: h.score, reverse=True)
        final_hits = all_hits[:limit]

        logger.info("Ricerca Lezioni completata", query=query, category=category, found=len(final_hits))
        return MemoryQueryResult(query=query or "", total_hits=len(final_hits), hits=final_hits)

    def search_all(
        self,
        query: str,
        category: str | None = None,
        limit: int = 20,
    ) -> MemoryQueryResult:
        """
        API richiesta: Combina sia Episode che Lesson in un framework aggregato.
        # 2026-04-02 23:45
        """
        episodes_res = self.search_episodes(query=query, category=category, limit=limit)
        lessons_res = self.search_lessons(query=query, category=category, limit=limit)
        
        combined_hits = episodes_res.hits + lessons_res.hits
        combined_hits.sort(key=lambda h: h.score, reverse=True)
        final_hits = combined_hits[:limit]
        
        logger.info("Ricerca All completata", query=query, category=category, found=len(final_hits))
        return MemoryQueryResult(query=query, total_hits=len(final_hits), hits=final_hits)

    def build_memory_context(
        self,
        query: str,
        category: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        API Riferimento: Raccoglie in dict semplice il context top utile per l'LLM o futuri agent.
        Il Summary deve essere deterministico e sintetico.
        # 2026-04-02 23:45
        """
        all_res = self.search_all(query=query, category=category, limit=limit)
        top_lessons = [h for h in all_res.hits if h.source_type == "lesson"]
        top_episodes = [h for h in all_res.hits if h.source_type == "episode"]
        
        cat_str = category if category else "tutte le categorie"
        summary = f"Trovate {len(top_lessons)} lesson rilevanti e {len(top_episodes)} episodi collegati a '{query}' su {cat_str}."
        
        if len(top_lessons) == 0 and len(top_episodes) == 0:
            summary = f"Nessun hit storico trovato nella memoria per la query '{query}' su {cat_str}."

        return {
            "query": query,
            "category": category,
            "summary": summary,
            "total_hits": len(all_res.hits),
            "top_lessons": [
                {
                    "title": l.title,
                    "excerpt": l.excerpt,
                    "score": l.score,
                    "path": l.path
                } for l in top_lessons
            ],
            "top_episodes": [
                {
                    "kind": e.kind,
                    "excerpt": e.excerpt,
                    "score": e.score,
                    "timestamp": e.timestamp
                } for e in top_episodes
            ]
        }
