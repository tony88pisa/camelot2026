# src/ai_trader/brain/code_evolver.py
import re
import ast
import json
from pathlib import Path
from datetime import datetime, timezone
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.core.ollama_client import OllamaClient
from ai_trader.memory.lesson_store import LessonStore

logger = get_logger("code_evolver")

class CodeEvolver:
    """
    Traduce le riflessioni dell'AI in codice Python eseguibile.
    Gestisce la generazione, la validazione e il salvataggio delle patch.
    """
    
    def __init__(self, ollama: OllamaClient = None, lesson_store: LessonStore = None):
        self.ollama = ollama or OllamaClient(model="gemma4:latest")
        self.lessons = lesson_store or LessonStore()
        
    def generate_patch(self, lesson_content: str, target_function: str, original_signature: str = None) -> dict:
        """
        Interroga Gemma 4 per scrivere il codice necessario a risolvere un problema.
        """
        logger.info(f"EVOLVER: Generazione patch neurale per {target_function}...")
        
        sig_requirement = f"FIRMATA ORIGINALE: {original_signature}" if original_signature else "Mantieni la firma della funzione originale."

        prompt = f"""
        [SYSTEM: NEURAL ARCHITECT v1.0]
        AI LESSON: {lesson_content}
        TARGET: {target_function}
        {sig_requirement}
        
        OBIETTIVO: Scrivi una versione ottimizzata della funzione Python '{target_function}' che risolva i problemi descritti nella lezione.
        
        REQUISITI MANDATORI:
        1. Solo codice Python puro al TOP LEVEL (ambito globale del modulo). NO classi.
        2. Non includere spiegazioni extra, solo il blocco di codice.
        3. Nomina la funzione esattamente: 'patch_{target_function.replace('.', '_')}'
        4. DEVI RISPETTARE ESATTAMENTE LA FIRMA (ARGOMENTI) RICHIESTA: {sig_requirement}
        5. NON AGGIUNGERE ARGOMENTI EXTRA. SE L'ORIGINALE HA (self, A, B), LA PATCH DEVE AVERE (self, A, B).
        6. RISPETTA IL TIPO DI RITORNO DELL'ORIGINALE (es. se l'originale restituisce str, la patch deve restituire str).
        7. Se la funzione originale usa 'self', mantienilo come primo argomento della funzione globale.
        8. Assicurati che limportazione dei moduli necessari sia inclusa (import math, decimal, etc).
        
        RISPONDI ESCLUSIVAMENTE CON IL CODICE TRA TRIPLE BACKTICKS.
        """
        
        res = self.ollama.chat([{"role": "user", "content": prompt}])
        if not res.get("ok"):
            return {"ok": False, "error": "AI Timeout"}
            
        raw_code = res["message"].get("content", "")
        code_match = re.search(r'```python\n(.*?)\n```', raw_code, re.DOTALL)
        if not code_match:
            code_match = re.search(r'```\n(.*?)\n```', raw_code, re.DOTALL)
            
        snippet = code_match.group(1) if code_match else raw_code
        
        # Validazione Sintattica
        if self._validate_syntax(snippet):
            logger.info(f"EVOLVER: Patch per {target_function} validata con successo.")
            return {"ok": True, "code": snippet}
        else:
            logger.error(f"EVOLVER: Patch per {target_function} ha errori di sintassi.")
            return {"ok": False, "error": "Syntax Error in AI Proposal"}

    def _validate_syntax(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def save_to_neural_registry(self, func_key: str, code: str):
        """
        Salva la patch nel file fisico, sovrascrivendo eventuali versioni precedenti dello stesso hook.
        """
        registry_path = Path("src/ai_trader/core/neural_patches_data.py")
        
        # Sincronizzazione con SuperMemory
        self.lessons.append_lesson(
            category="system",
            title=f"PROPOSTA PATCH NEURALE: {func_key}",
            content=f"L'AI ha generato il seguente codice per risolvere il problema:\n\n```python\n{code}\n```",
            tags=["neural_patch", "code_evolution", func_key]
        )
        
        # Carica il file corrente
        lines = []
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        
        # Rimuovi vecchia patch se presente (cerca il commento di header)
        new_lines = []
        skip = False
        header_marker = f"# --- Patch per {func_key}"
        
        for line in lines:
            if line.startswith(header_marker):
                skip = True
                continue
            if skip and line.startswith("# --- Patch per") or (skip and line.strip() == "" and len(new_lines) > 0 and new_lines[-1].startswith("# --- Patch per")):
                # Trovato inizio di un'altra patch, smetti di skippare
                skip = False
            
            if not skip:
                new_lines.append(line)
        
        # Aggiungi la nuova patch in coda
        new_lines.append(f"\n# --- Patch per {func_key} ({datetime.now(timezone.utc).isoformat()}) ---\n")
        new_lines.append(code + "\n")
        
        with open(registry_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
        # Forziamo il ricaricamento nel registro in memoria
        from ai_trader.core.neural_patches import init_neural_patches
        init_neural_patches()
            
        logger.info(f"EVOLVER: Patch salvata e attivata in memoria: {registry_path}")
