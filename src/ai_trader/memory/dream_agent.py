# src/ai_trader/memory/dream_agent.py
# 2026-04-02 23:15 - Dream Agent per la consolidazione della memoria
"""
Dream Agent
Legge gli episodi recenti dal memory core, individua pattern deterministici 
(errori ripetuti, raggruppamento per kind), e genera un Lesson consolidato in formato Markdown.
Aggiorna automaticamente il MEMORY.md alla fine del ciclo.
"""

from typing import Any
from datetime import datetime, timezone
import json

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.memory.memory_index import MemoryIndex

# 2026-04-02 23:15 - Logger per il Dream Agent
logger = get_logger("dream_agent")


class DreamAgent:
    """
    Agente di consolidazione della memoria (Dream Cycle).
    Analizza gli eventi passati per derivare Lezioni senza ancora l'uso di LLM.
    # 2026-04-02 23:15 - Creazione
    """

    def __init__(
        self,
        episodes: EpisodeStore | None = None,
        lessons: LessonStore | None = None,
        memory_index: MemoryIndex | None = None
    ):
        """
        Inizializza l'agente. Se gli store non vengono passati esplicitamente, 
        ne instanzia di default basati sui settings.
        # 2026-04-02 23:15
        """
        self.episodes = episodes or EpisodeStore()
        self.lessons = lessons or LessonStore()
        self.memory_index = memory_index or MemoryIndex()
        
        # Override per far usare gli stessi backend path al memory_index, per coerenza
        self.memory_index.episodes = self.episodes
        self.memory_index.lessons = self.lessons

        logger.info("DreamAgent inizializzato")

    def scan_recent_episodes(self, category: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Carica gli episodi recenti (per semplicità degli ultimi giorni fino ad oggi) 
        fino ad un limite numerico.
        # 2026-04-02 23:15
        """
        # Carica episodi senza filtro di data temporale restrittivo (da inizio) ma poi li taglia al `limit`
        # In un file store deterministico si caricherebbero a ritroso partendo da oggi. Ma usiamo il load che abbiamo.
        # Rileviamo il range.
        all_today = self.episodes.load_episodes(category)
        
        # Sort descrescente per timestamp (più recente prima) e prendi <limit> element
        all_today.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        recent = all_today[:limit]
        return recent

    def extract_candidate_patterns(self, episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Analisi deterministica di una lista di episodi.
        Rileva pattern come: kind multipli dello stesso tipo, errori ripetuti nei payload.
        # 2026-04-02 23:15
        """
        patterns = []
        if not episodes:
            return patterns

        counts_by_kind = {}
        error_counts = 0

        for ep in episodes:
            k = ep.get("kind", "unknown")
            counts_by_kind[k] = counts_by_kind.get(k, 0) + 1
            
            payload = ep.get("payload", {})
            if isinstance(payload, dict) and payload.get("ok") is False:
                error_counts += 1
            elif isinstance(payload, dict) and "error" in payload:
                error_counts += 1

        # Genera pattern candidati base
        for kind, count in counts_by_kind.items():
            if count >= 3:
                patterns.append({
                    "pattern_type": "frequent_kind",
                    "kind": kind,
                    "count": count,
                    "desc": f"Rilevata alta frequenza di '{kind}' ({count} eventi)",
                    "tags": ["frequency", kind]
                })

        if error_counts >= 2:
            patterns.append({
                "pattern_type": "repeated_errors",
                "count": error_counts,
                "desc": f"Rilevati {error_counts} errori ripetuti o eventi non-ok",
                "tags": ["error_avoidance", "alert"]
            })

        return patterns

    def _is_duplicate_lesson(self, category: str, title: str) -> bool:
        """Verifica grezza per non inserire doppioni nella stessa categoria. # 2026-04-02 23:15"""
        existing = self.lessons.read_lessons(category)
        for l in existing:
            if l.get("title") == title:
                return True
        return False

    def consolidate_lessons(self, category: str, limit: int = 100) -> list[str]:
        """
        Estrae gli episodi recenti, elabora pattern e, se ci sono insights validi,
        salva nuove lessons.
        # 2026-04-02 23:15
        
        Returns:
            list[str]: Nomi dei file lesson generati
        """
        episodes = self.scan_recent_episodes(category, limit)
        patterns = self.extract_candidate_patterns(episodes)
        
        generated_lessons = []
        
        for pat in patterns:
            title = f"Consolidazione deterministica: {pat.get('pattern_type')}"
            
            # Anti-duplicazione grezza
            if self._is_duplicate_lesson(category, title):
                logger.debug("Duplicato saltato", category=category, title=title)
                continue
                
            content = (
                f"L'agente di sogno ha consolidato le memory per la categoria '{category}'.\n\n"
                f"**Osservazione**: {pat.get('desc')}\n"
                f"**Timestamp di analisi**: {datetime.now(timezone.utc).isoformat()}\n\n"
                f"Questa è un'elaborazione generata automaticamente senza LLM per stabilire una base ricorrente."
            )
            
            tags = pat.get("tags", []) + ["dream_auto"]
            
            filename = self.lessons.append_lesson(
                category=category,
                title=title,
                content=content,
                tags=tags
            )
            if filename:
                generated_lessons.append(filename)
                
        return generated_lessons

    def run_dream_cycle(self, categories: list[str] | None = None) -> dict[str, Any]:
        """
        Avvia un ciclo completo consolidando le categorie indicate (o default)
        e chiama l'aggiornamento del MEMORY.md
        # 2026-04-02 23:15
        """
        cats_to_run = categories or ["trading", "research", "system"]
        
        logger.info("Inizio Dream Cycle", categories=cats_to_run)
        stats = {}
        total_lessons = 0
        
        for cat in cats_to_run:
            new_lessons = self.consolidate_lessons(cat)
            stats[cat] = len(new_lessons)
            total_lessons += len(new_lessons)
            
        # Al termine del ciclo, forziamo un refresh del Memory.md
        self.memory_index.update_memory_index()
        
        result = {
            "ok": True,
            "total_new_lessons": total_lessons,
            "breakdown": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Dream Cycle concluso", result=result)
        return result
