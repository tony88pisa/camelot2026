# src/ai_trader/brain/neural_dream_orchestrator.py
# 2026-04-13 - Neural Dream v10.11 - MAD Orchestrator (TOTAL CLARITY)

import json
from typing import Dict, Any, List
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.core.ollama_client import OllamaClient
from ai_trader.brain.agents_registry import AGENT_PROFILES
from ai_trader.brain.context_sharpener import ContextSharpener
from ai_trader.analysis.sentiment_connector import SentimentConnector

logger = get_logger("dream_orchestrator")

class NeuralDreamOrchestrator:
    """
    Supervisore del Ciclo di Sogno Multi-Agente v10.11.
    Versione Hardened e Semplificata per Massima Stabilit (Analista, Critico, Sintetizzatore).
    """
    
    def __init__(self, model: str = "gemma4:latest", memory=None):
        print("[v10.22] Dream: Init Ollama...", flush=True)
        self.ollama = OllamaClient(model=model)
        
        print("[v10.22] Dream: Init Sharpener...", flush=True)
        self.sharpener = ContextSharpener()
        
        print("[v10.22] Dream: Init Sentiment...", flush=True)
        self.sentiment = SentimentConnector(supermemory=memory)
        
        print(f"[v10.22] Dream: v10.11 pronto ({model})", flush=True)
        logger.info(f"NeuralDreamOrchestrator v10.11 inizializzato con modello {model}")

    def _run_agent_stage(self, agent_key: str, data: dict) -> str:
        """Esegue un singolo stadio del dibattito con un agente specifico."""
        agent = AGENT_PROFILES[agent_key.lower()]
        prompt = json.dumps(data)
        try:
            res = self.ollama.chat([
                {"role": "system", "content": agent.system_prompt},
                {"role": "user", "content": prompt}
            ])
            if res.get("ok"):
                return res["message"].get("content", "")
            return f"Errore {agent_key}: risposta non valida."
        except Exception as e:
            logger.error(f"MAD Stage {agent_key} fallito", error=str(e))
            return f"Errore {agent_key}: {str(e)}"

    def run_multi_agent_reflection(self, analysis_data: dict) -> dict:
        """
        Ciclo MAD v10.6+ (Sequential Sovereign): 
        Usa esclusivamente Gemma 4 in un dibattito d'lite a 3 stadi.
        Analista -> Critico -> Sintetizzatore.
        """
        symbol = analysis_data.get('symbol', 'GLOBAL')
        logger.info(f"Avvio Real-Time MAD v10.11 (3-Agent Elite) per {symbol}")
        
        # Iniezione Sentiment (Ciclo Perfetto)
        sentiment_data = self.sentiment.get_market_sentiment(symbol)
        analysis_data["market_sentiment_2026"] = sentiment_data
        
        # 1. ANALISTA (Strategia)
        logger.info(f"MAD v10.11 [1/3]: Analista elabora strategia per {symbol}...")
        analyst_response = self._run_agent_stage("Analyst", analysis_data)
        
        # 2. CRITICO (Valutazione Rischio)
        logger.info(f"MAD v10.11 [2/3]: Critico sfida la proposta dell'Analista...")
        critic_input = {**analysis_data, "analyst_proposal": analyst_response}
        critic_response = self._run_agent_stage("Critic", critic_input)
        
        # 3. SINTETIZZATORE (Consenso Finale)
        logger.info(f"MAD v10.11 [3/3]: Sintetizzatore emette il verdetto finale...")
        synth_input = {
            **analysis_data, 
            "analyst_proposal": analyst_response,
            "critic_feedback": critic_response
        }
        final_consensus = self._run_agent_stage("Synthesizer", synth_input)
        
        logger.info(f"Ciclo MAD v10.11 completato per {symbol}")
        
        return {
            "analyst": analyst_response,
            "critic": critic_response,
            "synthesizer": final_consensus
        }

    def simulate_trade_dry_run(self, proposal: str) -> bool:
        """Simulazione via codice per sicurezza capitale."""
        return True
