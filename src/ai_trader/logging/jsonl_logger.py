# src/ai_trader/logging/jsonl_logger.py
# 2026-04-02 21:05 - Logger JSONL per AI Trader
# Scrive ogni evento come riga JSON in un file .jsonl
"""
Logger JSONL strutturato.
Ogni log  una riga JSON con: timestamp, level, module, message, extra.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


class JsonlLogger:
    """
    Logger che scrive eventi in formato JSON Lines.
    # 2026-04-02 21:05 - Creazione classe JsonlLogger
    """

    LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}

    def __init__(
        self,
        module_name: str,
        log_dir: str | Path | None = None,
        log_level: str = "INFO",
        log_file: str = "ai_trader.jsonl",
    ):
        """
        Inizializza il logger.
        # 2026-04-02 21:05

        Args:
            module_name: nome del modulo che sta loggando
            log_dir: directory dei log (default: logs/ nella root)
            log_level: livello minimo di log (DEBUG/INFO/WARNING/ERROR/CRITICAL)
            log_file: nome del file di log
        """
        self.module_name = module_name
        self.log_level = self.LEVELS.get(log_level.upper(), 20)

        if log_dir is None:
            # Fallback: logs/ nella root del progetto
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            log_dir = project_root / "logs"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / log_file

    def _write(self, level: str, message: str, extra: dict | None = None) -> None:
        """
        Scrive un evento JSONL su file e console.
        # 2026-04-02 21:05
        """
        level_num = self.LEVELS.get(level.upper(), 20)
        if level_num < self.log_level:
            return

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "module": self.module_name,
            "message": message,
        }
        if extra:
            entry["extra"] = extra

        line = json.dumps(entry, ensure_ascii=False)

        # Scrivi su file con flush forzato (v10.8 Luminous Flow)
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                # Forza il sistema operativo a scrivere fisicamente sul disco
                try:
                    os.fsync(f.fileno())
                except:
                    pass 
        except OSError as e:
            print(f"[LOGGER ERROR] Cannot write to {self.log_path}: {e}", file=sys.stderr)

        # Stampa su console per debug
        if level_num >= self.LEVELS.get("WARNING", 30):
            print(f"[{level.upper()}] {self.module_name}: {message}", file=sys.stderr)

    def debug(self, message: str, **extra) -> None:
        """Log livello DEBUG. # 2026-04-02 21:05"""
        self._write("DEBUG", message, extra if extra else None)

    def info(self, message: str, **extra) -> None:
        """Log livello INFO. # 2026-04-02 21:05"""
        self._write("INFO", message, extra if extra else None)

    def warning(self, message: str, **extra) -> None:
        """Log livello WARNING. # 2026-04-02 21:05"""
        self._write("WARNING", message, extra if extra else None)

    def error(self, message: str, **extra) -> None:
        """Log livello ERROR. # 2026-04-02 21:05"""
        self._write("ERROR", message, extra if extra else None)

    def critical(self, message: str, **extra) -> None:
        """Log livello CRITICAL. # 2026-04-02 21:05"""
        self._write("CRITICAL", message, extra if extra else None)


# 2026-04-02 21:05 - Cache dei logger per modulo
_loggers: dict[str, JsonlLogger] = {}


def get_logger(module_name: str) -> JsonlLogger:
    """
    Restituisce un logger JSONL per il modulo specificato.
    Usa cache per evitare duplicati.
    # 2026-04-02 21:05
    """
    if module_name not in _loggers:
        # Usa le impostazioni centralizzate se disponibili
        log_dir = None
        log_level = "INFO"
        try:
            from ai_trader.config.settings import get_settings
            settings = get_settings()
            log_dir = settings.LOG_DIR
            log_level = settings.LOG_LEVEL
        except (ImportError, Exception):
            pass
        _loggers[module_name] = JsonlLogger(
            module_name=module_name,
            log_dir=log_dir,
            log_level=log_level,
        )
    return _loggers[module_name]
