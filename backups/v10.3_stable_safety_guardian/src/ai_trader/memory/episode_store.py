# src/ai_trader/memory/episode_store.py
# 2026-04-02 23:05 - Store per episodi (eventi, decisioni, osservazioni)
# Scrittura JSONL append-only, lettura robusta, classificazione per category
"""
EpisodeStore  storage persistente per episodi del bot diviso per categoria.

memdir/episodes/
 trading/
 research/
 system/
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.mcp.mcp_sse_handler import McpSseHandler


# 2026-04-02 23:05 - Logger per questo modulo
logger = get_logger("memory_episodes")

ALLOWED_CATEGORIES = {"trading", "research", "system"}


class EpisodeStore:
    """
    Store append-only per episodi, partizionato per categoria.
    # 2026-04-02 23:05 - Modifica design per supportare 'category'
    """

    def __init__(self, base_dir: str | Path | None = None):
        """# 2026-04-02 23:05"""
        if base_dir is None:
            from ai_trader.config.settings import get_settings
            base_dir = get_settings().MEMDIR / "episodes"

        self.base_dir = Path(base_dir)
        # Crea le directory di base per categoria
        for category in ALLOWED_CATEGORIES:
            (self.base_dir / category).mkdir(parents=True, exist_ok=True)
            
        # Inizializzazione SuperMemory Bridge
        from ai_trader.config.settings import get_settings
        st = get_settings()
        if st.SUPERMEMORY_TOKEN:
            self.mcp = McpSseHandler(st.SUPERMEMORY_URL, st.SUPERMEMORY_TOKEN)
            self.mcp_ready = self.mcp.connect()
        else:
            self.mcp = None
            self.mcp_ready = False
            
        logger.info("EpisodeStore inizializzato", base_dir=str(self.base_dir), mcp_sync=self.mcp_ready)

    def _get_file_path(self, category: str, dt: datetime | None = None) -> Path:
        """# 2026-04-02 23:05"""
        if dt is None:
            dt = datetime.now(timezone.utc)
        filename = dt.strftime("%Y-%m-%d") + ".jsonl"
        return self.base_dir / category / filename

    def append_episode(
        self,
        category: str,
        kind: str,
        payload: dict[str, Any],
        tags: list[str] | None = None,
        source: str = "",
    ) -> str:
        """
        API richiesta: Aggiunge un episodio allo store di una categoria.
        # 2026-04-02 23:05

        Args:
            category: 'trading', 'research' o 'system'
            kind: tipo di episodio (es. "market_observation")
            payload: dati dell'episodio
            tags: lista di tag (opzionale)
            source: sorgente dell'episodio
            
        Returns:
            str: ID dell'episodio generato
        """
        if category not in ALLOWED_CATEGORIES:
            logger.warning("Categoria non standard utilizzata", category=category)
            (self.base_dir / category).mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc)
        episode_id = str(uuid.uuid4())
        episode = {
            "id": episode_id,
            "timestamp": now.isoformat(),
            "kind": kind,
            "source": source,
            "tags": tags or [],
            "payload": payload,
        }

        file_path = self._get_file_path(category, now)
        try:
            line = json.dumps(episode, ensure_ascii=False, default=str)
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
            logger.info("Episodio salvato localmente", id=episode_id, category=category, kind=kind)
            
            # Sincronizzazione con SuperMemory
            if self.mcp_ready:
                self._sync_to_supermemory(episode, category)

        except OSError as e:
            logger.error("Errore scrittura episodio", error_msg=str(e), file=str(file_path))

        return episode_id

    def _sync_to_supermemory(self, episode: dict[str, Any], category: str):
        """Invia una rappresentazione semantica dell'episodio a SuperMemory."""
        try:
            kind = episode.get("kind", "unknown")
            payload = episode.get("payload", {})
            tags = ", ".join(episode.get("tags", []))
            
            # Costruiamo una stringa semantica per il grafo
            # Il tool 'memory' di SuperMemory accetta 'input' come testo da analizzare e salvare
            content = f"[KIND: {kind}] [CAT: {category}] [TAGS: {tags}] Event: {json.dumps(payload, default=str)}"
            
            res = self.mcp.call_tool("memory", {"content": content})
            if res.get("ok"):
                logger.debug("Episodio sincronizzato su SuperMemory", id=episode["id"])
            else:
                logger.warning("Sincronizzazione SuperMemory fallita", error=res.get("error"))
        except Exception as e:
            logger.error("Eccezione durante sync SuperMemory", error=str(e))

    def load_episodes(
        self,
        category: str,
        since: str | datetime | None = None,
        until: str | datetime | None = None,
    ) -> list[dict[str, Any]]:
        """
        API richiesta: Carica episodi di una categoria, con filtri data opzionali.
        # 2026-04-02 23:05
        """
        from datetime import timedelta
        
        cat_dir = self.base_dir / category
        if not cat_dir.exists():
            return []

        # Default a log di "oggi" se since/until non specificati
        if since is None and until is None:
            since = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            until = since + timedelta(days=1)

        # Parse date
        if isinstance(since, str) and since:
            since_dt = datetime.strptime(since.split("T")[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        elif since:
            since_dt = since
        else:
            since_dt = datetime.min.replace(tzinfo=timezone.utc)

        if isinstance(until, str) and until:
            until_dt = datetime.strptime(until.split("T")[0], "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        elif until:
            until_dt = until
        else:
            until_dt = datetime.max.replace(tzinfo=timezone.utc)

        episodes: list[dict[str, Any]] = []
        current = since_dt
        while current <= until_dt and current.year < 2100: # Prevenzione loop inf in caso datetime.max
            file_path = self._get_file_path(category, current)
            episodes.extend(self._read_jsonl(file_path))
            current += timedelta(days=1)

        return episodes

    def _read_jsonl(self, file_path: Path) -> list[dict[str, Any]]:
        """Legge JSONL skippando righe corrotte. # 2026-04-02 23:05"""
        if not file_path.exists():
            return []

        results: list[dict[str, Any]] = []
        corrupt_count = 0

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        results.append(entry)
                    except json.JSONDecodeError:
                        corrupt_count += 1
                        logger.warning("Riga corrotta skippata", file=file_path.name, line_num=line_num)
        except OSError as e:
            logger.error("Errore lettura file", error_msg=str(e), file=str(file_path))

        if corrupt_count > 0:
            logger.warning("Righe corrotte trovate", file=file_path.name, count=corrupt_count)

        return results
