# src/ai_trader/brain/brain_agent.py
import re
import json
from pathlib import Path
from datetime import datetime
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.core.ollama_client import OllamaClient

logger = get_logger("brain_agent")

class BrainAgent:
    """
    Il 'Comandante Strategico' del sistema Quantum Hunter.
    Coordina memoria, analisi macro e decisioni operative.
    """

    def __init__(self, lessons: LessonStore = None):
        print("[v10.18] Brain: Inizio Init...", flush=True)
        self.lessons = lessons or LessonStore()
        print("[v10.18] Brain: LessonStore OK.", flush=True)
        self.ollama = OllamaClient(model="gemma4:latest")
        print("[v10.18] Brain: OllamaClient OK.", flush=True)
        self.rules = []
        self._load_rules()
        print("[v10.18] Brain: Regole OK.", flush=True)

    def _load_rules(self):
        """Carica le regole operative consolidate dalle lezioni."""
        logger.info("Brain: Caricamento regole dalla memoria...")
        found_rules = []
        # Legge lezioni trading e system
        for category in ["trading", "system"]:
            lesson_files = self.lessons.read_lessons(category)
            for l_info in lesson_files:
                try:
                    with open(l_info["path"], "r", encoding="utf-8") as f:
                        content = f.read()
                        # Cerca pattern "REGOLA: [testo]" - Versione ultra-robusta v8.1.2
                        matches = re.findall(r'(?i)REGOLA:\s*(.*)', content)
                        for m in matches:
                            clean_rule = m.strip()
                            if clean_rule:
                                found_rules.append(clean_rule)
                except Exception as e:
                    logger.error(f"Brain: Errore lettura file {l_info['filename']}", error=str(e))
        
        self.rules = list(set(found_rules)) # Unici
        logger.info(f"Brain: {len(self.rules)} regole attive caricate.")

    def evaluate_strategy(self, symbol: str, budget: float, market_analysis: dict = None) -> dict:
        """
        Valuta se una mossa proposta dal HunterAgent  compatibile con la memoria e la strategia macro.
        """
        logger.info(f"Brain: Consultazione strategica per {symbol} (Budget: {budget:.2f})")
        
        # 1. PROTOCOLLO DI RIFLESSO (Istantaneo - No AI)
        logger.debug(f"Brain DEBUG: Inizio Protocollo Riflesso per {symbol}")
        if budget < 10.50:
            # Rigetto forzato solo per i 'Giganti' che richiedono alta liquidit per ordine
            very_institutional = ["BTC", "ETH"]
            if any(asset in symbol.upper() for asset in very_institutional):
                return {
                    "ok": False, 
                    "reason": f"Protocollo Riflesso: Budget {budget} insufficiente per asset istituzionale {symbol} (Min: 10.50)",
                    "action": "SKIP"
                }
        logger.debug("Brain DEBUG: Protocollo Riflesso superato o asset compatibile per analisi")
        logger.debug("Brain DEBUG: Protocollo Riflesso superato")

        # 2. Controllo Regole dalla Memoria (Deterministico)
        for rule in self.rules:
            # Se la regola menziona il budget e l'asset corrente, applicala subito
            rule_l = rule.lower()
            # Cerca il simbolo come parola intera per evitare che 'ada' faccia match con 'metadati'
            symbol_pattern = r'\b' + re.escape(symbol.lower()[:3]) + r'\b'
            if "budget" in rule_l and re.search(symbol_pattern, rule_l):
                 return {
                    "ok": False, 
                    "reason": f"Violazione Regola Strategica: {rule}",
                    "action": "SKIP"
                }

        # 3. Consultazione Intelligence Recente (RAG v8.5)
        recent_news = ""
        if hasattr(self.lessons, 'mcp_ready') and self.lessons.mcp_ready:
            try:
                logger.debug(f"Brain: Ricerca news su SuperMemory per {symbol}...")
                # Cerchiamo memorie correlate al simbolo
                query = f"ultime notizie e sentiment per {symbol}"
                res = self.lessons.mcp.call_tool("recall", {"query": query})
                if res.get("ok") and "result" in res:
                    memories = res["result"].get("memories", [])
                    if memories:
                        recent_news = "\n".join([m.get("content", "") for m in memories[:3]])
                        logger.info(f"Brain: Recuperate {len(memories[:3])} news rilevanti per {symbol}")
            except Exception as e:
                logger.warning(f"Brain: Errore RAG SuperMemory: {e}")

        # 4. Consultazione AI (Strategia Autonoma v8.5 Sentinel)
        prompt = f"""
        [SYSTEM: QUANTUM HUNTER STRATEGIST v8.5]
        ANALISI TECNICA: {json.dumps(market_analysis, default=str)}
        CAPITALE: {budget} EUR | ASSET: {symbol}
        
        [INTELLIGENCE RECENTE DA SUPERMEMORY]:
        {recent_news if recent_news else "Nessuna notizia recente in memoria."}
        
        REQUISITO: Binance richiede ~10 EUR, ma coppie come {symbol} possono accettare 5-8 EUR.
        
        RISPONDI ESCLUSIVAMENTE CON QUESTO JSON (MASSIMA DENSIT):
        {{
            "decision": "APPROVE" | "REJECT",
            "reason": "SPIEGAZIONE (Max 150 parole). Integra INDICATORI TECNICI + NOTIZIE RECENTI (se presenti).",
            "suggested_asset": "{symbol}"
        }}
        """
        
        # Chiamata con timeout specifico per la consultazione rapida
        res = self.ollama.chat([{"role": "user", "content": prompt}], timeout=60, max_tokens=800)
        
        if res.get("ok"):
            try:
                # Reperiamo solo il JSON dall'output
                raw_content = res["message"]["content"]
                json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group())
                    logger.info(f"Brain Decision: {decision['decision']} - {decision['reason']}")
                    return {
                        "ok": decision["decision"] == "APPROVE",
                        "reason": decision["reason"],
                        "suggested_asset": decision.get("suggested_asset")
                    }
            except Exception as e: 
                logger.warning(f"Brain: Errore parsing AI: {e}")

        # 3. FALLBACK DI EMERGENZA (Se AI va in timeout o errore)
        logger.warning(f"Brain: Timeout/Errore AI. Attivazione Protocollo di Riflesso per {symbol}.")
        
        # Se siamo sotto i 10.50 EUR e proviamo a prendere una moneta grossa, blocca per sicurezza
        if budget < 10.50 and any(x in symbol.upper() for x in ["BTC", "ETH", "BNB", "SOL"]):
            return {
                "ok": False, 
                "reason": "Protocollo Riflesso: Budget critico per asset istituzionale (Safety Fallback)",
                "action": "SKIP"
            }

        return {"ok": True, "reason": "Protocollo Riflesso: Nessun rischio critico rilevato (Safety Fallback)."}
