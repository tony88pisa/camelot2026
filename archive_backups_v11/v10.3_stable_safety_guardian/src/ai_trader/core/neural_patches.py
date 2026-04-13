# src/ai_trader/core/neural_patches.py
import os
import sys
import importlib
import traceback
from pathlib import Path
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("neural_patches")

# Registro globale delle funzioni sovrascritte
_NEURAL_OVERRIDES = {}

def get_neural_override(func_key: str):
    """
    Recupera una funzione ottimizzata dall'AI se disponibile.
    func_key esempio: 'BinanceAdapter.format_quantity'
    """
    return _NEURAL_OVERRIDES.get(func_key)

def register_patch(func_key: str, func_obj):
    """Registra una nuova funzione corretta dall'AI."""
    _NEURAL_OVERRIDES[func_key] = func_obj
    logger.info(f"PATCH: Iniezione neurale completata per {func_key}")

def load_patches_from_file(patch_file: Path):
    """
    Carica dinamicamente le patch salvate nel file neural_patches.py.
    """
    if not patch_file.exists():
        return False
        
    try:
        # Caricamento dinamico del file di patch
        spec = importlib.util.spec_from_file_location("dynamic_patches", patch_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, "GET_PATCH_REGISTRY"):
            registry = module.GET_PATCH_REGISTRY()
            for key, func in registry.items():
                register_patch(key, func)
            return True
    except Exception as e:
        logger.error(f"PATCH: Errore caricamento file patch: {e}")
        return False

# Struttura base del file di patch che l'AI andr a scrivere
BASE_PATCH_TEMPLATE = """# ARCHIVIO PATCH NEURALI - QUANTUM HUNTER
import math

# --- SEZIONE PATCH GENERATE DALL'AI ---
"""

# Caricamento iniziale all'import del modulo
PATCH_DATA_FILE = Path("src/ai_trader/core/neural_patches_data.py")
if not PATCH_DATA_FILE.exists():
    with open(PATCH_DATA_FILE, "w", encoding="utf-8") as f:
        f.write(BASE_PATCH_TEMPLATE)

def init_neural_patches():
    """Inizializza il sistema caricando le patch dal file fisico."""
    try:
        with open(PATCH_DATA_FILE, "r", encoding="utf-8") as f:
            code = f.read()
        
        # Esecuzione sicura in un namespace dedicato
        namespace = {"math": __import__("math")}
        exec(code, namespace)
        
        # Estraiamo tutte le funzioni che iniziano con 'patch_'
        for name, func in namespace.items():
            if name.startswith("patch_"):
                # Esempio: patch_BinanceAdapter_format_quantity -> BinanceAdapter.format_quantity
                # Usiamo la prima occorrenza di _ (dopo patch_) per separare Classe e Metodo
                parts = name.replace("patch_", "").split("_", 1)
                if len(parts) == 2:
                    key = f"{parts[0]}.{parts[1]}"
                    register_patch(key, func)
                
    except Exception as e:
        logger.error(f"PATCH: Errore durante l'inizializzazione delle patch: {e}")

# Inizializza subito
init_neural_patches()
