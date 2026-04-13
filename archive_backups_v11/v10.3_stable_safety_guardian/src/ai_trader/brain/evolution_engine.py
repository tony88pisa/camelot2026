# src/ai_trader/brain/evolution_engine.py
import json
from pathlib import Path
from datetime import datetime, timezone
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.brain.code_evolver import CodeEvolver

logger = get_logger("evolution_engine")

class EvolutionEngine:
    """
    Il cuore dell'auto-evoluzione: traduce le lezioni imparate in cambiamenti di configurazione.
    Permette all'AI di auto-modificarsi per ottimizzare i profitti.
    """
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.lesson_store = LessonStore()
        self.evolver = CodeEvolver(lesson_store=self.lesson_store)
        self.evolution_log_path = config_path.parent / "evolution_log.jsonl"
        
    def _load_config(self) -> dict:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_config(self, config: dict):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
            
    def log_evolution(self, change_summary: str, old_value: any, new_value: any):
        """Registra ogni auto-modifica fatta dall'AI."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "change": change_summary,
            "old": old_value,
            "new": new_value
        }
        with open(self.evolution_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def apply_evolutionary_changes(self, ai_suggestions: dict):
        """
        Riceve suggerimenti dall'AI (es. nuove monete, cambio livelli) 
        e aggiorna la configurazione reale.
        """
        if not ai_suggestions: return
        
        current_config = self._load_config()
        changed = False
        
        # Esempio: Aggiornamento Monete in Whitelist
        if "suggested_whitelist" in ai_suggestions:
            old = current_config.get("WHITELIST_PAIRS", [])
            new = ai_suggestions["suggested_whitelist"]
            if old != new:
                current_config["WHITELIST_PAIRS"] = new
                self.log_evolution("Update Whitelist", old, new)
                logger.info(f"EVOLUTION: Whitelist aggiornata in autonomia: {new}")
                changed = True
                
        # Esempio: Aggiornamento Livelli Griglia
        if "suggested_grid_levels" in ai_suggestions:
            old = current_config.get("GRID_LEVELS", 8)
            new = int(ai_suggestions["suggested_grid_levels"])
            if old != new:
                current_config["GRID_LEVELS"] = new
                self.log_evolution("Update Grid Levels", old, new)
                logger.info(f"EVOLUTION: Livelli griglia aggiornati a {new}")
                changed = True

        # --- [NEW] Gestione Profili Macro v5.5 ---
        if "market_mode" in ai_suggestions:
            old_mode = current_config.get("MARKET_MODE", "BALANCED")
            new_mode = ai_suggestions["market_mode"]
            if old_mode != new_mode:
                current_config["MARKET_MODE"] = new_mode
                # Applica parametri specifici del profilo
                if new_mode == "WAR_HEDGE":
                    current_config["MAX_ORDER_USDT"] = 5.0  # Pi piccoli e cauti
                    current_config["WHITELIST_PAIRS"] = ["BTCUSDT", "PAXGUSDT"] # Bitcoin e Oro
                elif new_mode == "RECOVERY":
                    current_config["MAX_ORDER_USDT"] = 10.0
                    current_config["WHITELIST_PAIRS"] = ["XRPUSDT", "DOGEUSDT", "SOLUSDT"]
                
                self.log_evolution(f"Switch Market Mode to {new_mode}", old_mode, new_mode)
                logger.info(f"EVOLUTION: Cambiata modalit strategica globale: {new_mode}")
                changed = True

        if changed:
            self._save_config(current_config)
            return True
        return False

    def evolve_from_lessons(self, category: str = "trading"):
        """Analizza le ultime lezioni e decide se  necessaria un'evoluzione (Config e Code)."""
        category_dir = self.lesson_store.base_dir / category
        lesson_files = list(category_dir.glob("*.md"))
        if not lesson_files: return
        
        # Prendi lultima lezione
        latest_file = sorted(lesson_files)[-1]
        logger.info(f"EVOLUTION: Analisi file lezione {latest_file.name}")
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read()

        # --- LOGICA EVOLUZIONE CODICE (v10.0 - MAD Consensus) ---
        is_mad_certified = "CERTIFICAZIONE DI SICUREZZA: APPROVATA" in content.upper()
        keywords = ["raccomandazione", "raccomandate", "suggerimento", "azione correttiva", "riflessione ai mad"]
        
        if (is_mad_certified or any(k in content.lower() for k in keywords)) and "esecuzione" in content.lower():
            logger.info("EVOLUTION: Rilevato suggerimento per correzione codice (MAD Verified)" if is_mad_certified else "EVOLUTION: Rilevato suggerimento per correzione codice")
            # Esempio: L'AI ha identificato un problema in BinanceAdapter
            res = self.evolver.generate_patch(
                content, 
                "BinanceAdapter.format_quantity",
                original_signature="(self, symbol: str, quantity: float) -> str"
            )
            if res.get("ok"):
                self.evolver.save_to_neural_registry("BinanceAdapter.format_quantity", res["code"])
                self.log_evolution("Neural Code Patch", "Original Logic", "AI Optimized Snippet")
                return True
        return False
