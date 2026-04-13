# src/ai_trader/memory/memory_index.py
# 2026-04-02 23:08 - Indice della memoria in Markdown
# Genera memdir/index/MEMORY.md
"""
MemoryIndex  costruttore dell'indice leggibile della memoria.

L'API `update_memory_index()` legge gli episodi e le lezioni recenti 
e costruisce o aggiorna un file MEMORY.md centralizzato per visione umana/LLM.
"""

from datetime import datetime, timezone
from pathlib import Path

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.memory.episode_store import EpisodeStore, ALLOWED_CATEGORIES as EPISODES_CAT
from ai_trader.memory.lesson_store import LessonStore, ALLOWED_CATEGORIES as LESSONS_CAT

# 2026-04-02 23:08 - Logger
logger = get_logger("memory_index")


class MemoryIndex:
    """
    Costruisce l'indice MEMORY.md.
    # 2026-04-02 23:08
    """

    def __init__(self, base_dir: str | Path | None = None):
        """# 2026-04-02 23:08"""
        if base_dir is None:
            from ai_trader.config.settings import get_settings
            base_dir = get_settings().MEMDIR / "index"
            
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.base_dir / "MEMORY.md"

        # Dipendenze path implicite via settings (o custom se dir di test)
        memdir = self.base_dir.parent
        self.episodes = EpisodeStore(memdir / "episodes")
        self.lessons = LessonStore(memdir / "lessons")
        
        logger.info("MemoryIndex inizializzato", index_file=str(self.index_file))

    def update_memory_index(self) -> None:
        """
        API richiesta: Rigenera/Aggiorna il file memdir/index/MEMORY.md
        con il sunto di episodi e lesson.
        # 2026-04-02 23:08
        """
        now = datetime.now(timezone.utc)
        today_str = now.strftime("%Y-%m-%d")
        
        md_lines = [
            "# AI Trader Memory Index",
            f"Ultimo aggiornamento: {now.isoformat()}",
            "",
            "##  Lesson Importanti"
        ]
        
        # 2026-04-02 23:08 - Aggiungi elenco lessons
        has_lessons = False
        for cat in LESSONS_CAT:
            lessons = self.lessons.read_lessons(cat)
            if lessons:
                has_lessons = True
                md_lines.append(f"### {cat.capitalize()}")
                # Mostra le ultime 5 lezioni
                for l in lessons[-5:]:
                    md_lines.append(f"- **{l['title']}** (`{l['filename']}`)")
                md_lines.append("")
                
        if not has_lessons:
            md_lines.append("_Nessuna lezione registrata._\n")
            
        md_lines.append("##  Episodi Recenti (Oggi)")
        
        # 2026-04-02 23:08 - Aggiungi riepilogo episodi di oggi
        for cat in EPISODES_CAT:
            md_lines.append(f"### {cat.capitalize()}")
            episodes_today = self.episodes.load_episodes(cat, since=today_str, until=today_str)
            if episodes_today:
                counts_by_kind = {}
                for ep in episodes_today:
                    kind = ep.get("kind", "unknown")
                    counts_by_kind[kind] = counts_by_kind.get(kind, 0) + 1
                    
                for kind, count in counts_by_kind.items():
                    md_lines.append(f"- {kind}: {count} eventi")
            else:
                md_lines.append("_Nessun episodio oggi._")
            md_lines.append("")
            
        # Scrittura file
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                f.write("\n".join(md_lines))
            logger.info("MEMORY.md aggiornato con successo", file=self.index_file.name)
        except OSError as e:
            logger.error("Errore scrittura MEMORY.md", error_msg=str(e))
