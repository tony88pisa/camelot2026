# src/ai_trader/memory/lesson_store.py
# 2026-04-02 23:06 - Store per lezioni in formato Markdown
# Implementa: memdir/lessons/trading/YYYY-MM-DD-lesson-001.md
"""
LessonStore — storage persistente per lezioni apprese dal bot, salvate come Markdown.

memdir/lessons/
├── trading/
└── system/
"""

import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ai_trader.logging.jsonl_logger import get_logger

# 2026-04-02 23:06 - Logger per questo modulo
logger = get_logger("memory_lessons")

ALLOWED_CATEGORIES = {"trading", "system"}


class LessonStore:
    """
    Gestisce il salvataggio di lesson in file Markdown leggibili.
    Ogni lesson è un file separato.
    # 2026-04-02 23:06 - Creazione classe LessonStore Markdown
    """

    def __init__(self, base_dir: str | Path | None = None):
        """# 2026-04-02 23:06"""
        if base_dir is None:
            from ai_trader.config.settings import get_settings
            base_dir = get_settings().MEMDIR / "lessons"

        self.base_dir = Path(base_dir)
        # 2026-04-02 23:06 - Crea cartelle di categoria base
        for category in ALLOWED_CATEGORIES:
            (self.base_dir / category).mkdir(parents=True, exist_ok=True)
            
        logger.info("LessonStore Markdown inizializzato", base_dir=str(self.base_dir))

    def _get_next_filename(self, category_dir: Path, date_str: str) -> Path:
        """
        Determina il prossimo nome file progressivo per la giornata.
        Esempio: 2026-04-02-lesson-001.md
        # 2026-04-02 23:06
        """
        prefix = f"{date_str}-lesson-"
        max_num = 0
        
        if category_dir.exists():
            for f in category_dir.glob(f"{prefix}*.md"):
                match = re.search(r'-lesson-(\d+)\.md$', f.name)
                if match:
                    num = int(match.group(1))
                    if num > max_num:
                        max_num = num
                        
        next_num = max_num + 1
        return category_dir / f"{prefix}{next_num:03d}.md"

    def append_lesson(
        self,
        category: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> str:
        """
        API richiesta: Aggiunge una lesson (scrive un file Markdown).
        # 2026-04-02 23:06

        Args:
            category: 'trading' o 'system'
            title: titolo della lesson
            content: contenuto Markdown della lesson
            tags: lista di tag (opzionale)

        Returns:
            str: path relativo o ID del file creato
        """
        if category not in ALLOWED_CATEGORIES:
            logger.warning("Categoria lesson non standard utilizzata", category=category)
            
        cat_dir = self.base_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        file_path = self._get_next_filename(cat_dir, date_str)
        lesson_id = str(uuid.uuid4())
        
        tags_str = ", ".join(tags) if tags else "none"
        
        # 2026-04-02 23:06 - Costruiamo il Markdown file con frontmatter/header
        md_content = f"""---
id: {lesson_id}
date: {now.isoformat()}
category: {category}
tags: [{tags_str}]
---

# {title}

{content}
"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(md_content)
            logger.info("Lesson Markdown creata", filepath=file_path.name, title=title)
            return file_path.name
        except OSError as e:
            logger.error("Errore scrittura lesson MD", error_msg=str(e), file=str(file_path))
            return ""

    def read_lessons(self, category: str) -> list[dict[str, str]]:
        """
        Legge tutte le lessons di una categoria (utile per l'index).
        Ritorna liste di dict con metadata di base parsato dal file.
        # 2026-04-02 23:06
        """
        cat_dir = self.base_dir / category
        if not cat_dir.exists():
            return []
            
        lessons = []
        for file_path in sorted(cat_dir.glob("*.md")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    
                # ESTRAZIONE GREZZA TITOLO DA MARKDOWN #...
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else file_path.stem
                
                # Timestamp dal file name come fallback
                lessons.append({
                    "filename": file_path.name,
                    "title": title,
                    "path": str(file_path),
                })
            except Exception as e:
                logger.warning("Impossibile leggere lesson", file=file_path.name, error=str(e))
                
        return lessons
