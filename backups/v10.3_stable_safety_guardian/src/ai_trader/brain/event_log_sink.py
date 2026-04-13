# src/ai_trader/brain/event_log_sink.py
# 2026-04-03 01:50 - Buffer Sink as heavy event auditor
"""
Sistema di Sink per la coda Logger pesante del Brain. Non blocca i calcoli, 
mette in hold logiche e binda ad un JSONL per la Dashboard / Auditing in append.
"""

import os
import json
import threading
from typing import Any
from pathlib import Path
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("event_sink")

class EventLogSink:
    """Implementa sink ad alta efficienza thread-safe da svuotare per file."""
    
    def __init__(self, directory: str = "memdir/logs/brain"):
        self.directory = directory
        self.queue: list[dict[str, Any]] = []
        self.lock = threading.Lock()
        self.initialized = False
        self.file_path = ""
    
    def initialize(self, active_date_override: str | None = None):
        """Bind target file."""
        with self.lock:
            Path(self.directory).mkdir(parents=True, exist_ok=True)
            from datetime import datetime, timezone
            dt = active_date_override or datetime.now(timezone.utc).strftime("%Y-%m-%d")
            self.file_path = os.path.join(self.directory, f"{dt}.jsonl")
            self.initialized = True
        
        # Flush code pendenti dopo il bind
        self.flush()

    def record_event(self, event_dict: dict[str, Any]):
        """Aggiunge evento al pool pesante."""
        with self.lock:
            self.queue.append(event_dict)
            
        if self.initialized:
            self.flush()
            
    def flush(self):
        """Svuota coda salvando su disco."""
        if not self.initialized or not self.file_path:
            return
            
        pulled = []
        with self.lock:
            if not self.queue:
                return
            pulled = self.queue[:]
            self.queue.clear()
            
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                for el in pulled:
                    f.write(json.dumps(el) + "\n")
        except Exception as e:
            logger.error("Failed writing jsonl heavy sync", error=str(e))
            # Restore coda se crash filesystem
            with self.lock:
                self.queue = pulled + self.queue

# Singleton base exporter
global_event_sink = EventLogSink()

def initialize_event_log_sink(directory_override: str | None = None):
    if directory_override:
        global_event_sink.directory = directory_override
    global_event_sink.initialize()

def push_event(evt: dict[str, Any]):
    global_event_sink.record_event(evt)
