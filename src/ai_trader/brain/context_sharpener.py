# src/ai_trader/brain/context_sharpener.py
# 2026-04-13 - Context Sharpener v1.0 (Token Reduction)

import json
from typing import List, Dict, Any
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("context_sharpener")

class ContextSharpener:
    """
    Ottimizzatore del contesto per i modelli locali.
    Riduce il numero di token filtrando dati ridondanti e troncando testi lunghi,
    preservando i dati tecnici critici (prezzi, RSI, timestamp).
    """

    def __init__(self, token_budget_approximation: int = 3000):
        # Budget indicativo in token (1 token ~ 4 caratteri o 1.3 parole)
        self.token_budget = token_budget_approximation
        # Campi tecnici da non toccare mai
        self.essential_fields = {"timestamp", "symbol", "price", "rsi", "trend", "regime", "rec", "level", "qty"}

    def estimate_tokens(self, text: str) -> int:
        """Stima grossolana dei token basata sulla lunghezza (1 token ~ 4 char)."""
        return len(text) // 4

    def sharpen_episodes(self, episodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pulisce e compatta una lista di episodi.
        """
        if not episodes:
            return []

        sharpened = []
        reduction_count = 0
        total_chars_in = 0
        total_chars_out = 0

        for ep in episodes:
            raw_ep_str = json.dumps(ep)
            total_chars_in += len(raw_ep_str)
            
            # Crea una copia per non modificare l'originale in memoria/DB
            new_ep = {}
            
            # 1. Mantieni i campi essenziali
            for field in self.essential_fields:
                if field in ep:
                    new_ep[field] = ep[field]
                elif "extra" in ep and field in ep["extra"]:
                    new_ep[field] = ep["extra"][field]

            # 2. Gestione News: Tronca contenuti narrativi lunghi
            if ep.get("kind") == "market_news" or ep.get("category") == "research":
                content = ep.get("message", "")
                # Se la news  troppo lunga, prendi solo l'essenziale (titolo + incipit)
                if len(content) > 300:
                    new_ep["info"] = content[:280] + "..."
                    reduction_count += 1
                else:
                    new_ep["info"] = content
                
                # Riduciamo il kind a sigla per risparmiare token
                new_ep["k"] = "news"
            else:
                # Per altri tipi di episodi, portiamo il messaggio ma lo limitiamo
                msg = ep.get("message", "")
                if len(msg) > 150:
                    new_ep["msg"] = msg[:140] + "..."
                else:
                    new_ep["msg"] = msg
                
                if "kind" in ep:
                    new_ep["k"] = ep["kind"]

            sharpened.append(new_ep)
            total_chars_out += len(json.dumps(new_ep))

        # Log delle prestazioni del compressore
        savings = 0
        if total_chars_in > 0:
            savings = 100 - (total_chars_out * 100 // total_chars_in)
        
        logger.info(f"Sharpening completato: Risparmio token stimato del {savings}%", 
                    in_chars=total_chars_in, 
                    out_chars=total_chars_out,
                    pruned_news=reduction_count)

        return sharpened

    def sharpen_message_history(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Riduce la cronologia dei messaggi del dibattito se troppo lunga.
        """
        # Implementazione futura se i dibattiti diventano troppo lunghi (>10 turni)
        return messages
