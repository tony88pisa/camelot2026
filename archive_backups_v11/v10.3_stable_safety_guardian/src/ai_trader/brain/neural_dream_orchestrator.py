# src/ai_trader/brain/neural_dream_orchestrator.py
# 2026-04-13 - Neural Dream v10.0 - MAD Orchestrator

import json
from datetime import datetime
from typing import Dict, Any, List

from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.core.ollama_client import OllamaClient
from ai_trader.brain.agents_registry import AGENT_PROFILES, get_base_dream_prompt, get_critic_prompt, get_final_consensus_prompt
from ai_trader.brain.context_sharpener import ContextSharpener

logger = get_logger("dream_orchestrator")

class NeuralDreamOrchestrator:
    """
    Supervisore del Ciclo di Sogno Multi-Agente.
    Coordina il dibattito tra Analista e Critico per produrre una lezione sicura.
    """
    
    def __init__(self, model: str = "gemma4:latest"):
        self.ollama = OllamaClient(model=model)
        self.sharpener = ContextSharpener()
        logger.info("NeuralDreamOrchestrator pronto con modello", model=model)

    def run_multi_agent_reflection(self, category: str, context: str, episodes: List[Dict[str, Any]]) -> str:
        """
        Esegue il dibattito a 3 stadi (MAD - Multi-Agent Debate).
        """
        # --- SHARPENING CONTEXT (v10.1) ---
        refined_episodes = self.sharpener.sharpen_episodes(episodes)
        episodes_json = json.dumps(refined_episodes, default=str)
        
        # --- FASE 1: ANALISI (Generazione Proposta) ---
        analyst = AGENT_PROFILES["analyst"]
        base_prompt = get_base_dream_prompt(category, context, episodes_json)
        
        logger.info(f"Fase 1: {analyst.name} sta analizzando...")
        analyst_res = self.ollama.chat([
            {"role": "system", "content": analyst.system_prompt},
            {"role": "user", "content": base_prompt}
        ])
        
        if not analyst_res.get("ok"):
            logger.error("Fallimento in Fase 1 (Analista)")
            return ""
        
        proposal = analyst_res["message"].get("content", "")
        
        # --- FASE 2: CRITICA (Technical Audit) ---
        critic = AGENT_PROFILES["critic"]
        critic_prompt = get_critic_prompt(proposal)
        
        logger.info(f"Fase 2: {critic.name} sta esaminando la proposta...")
        critic_res = self.ollama.chat([
            {"role": "system", "content": critic.system_prompt},
            {"role": "user", "content": critic_prompt}
        ])
        
        if not critic_res.get("ok"):
            logger.error("Fallimento in Fase 2 (Critico)")
            # In caso di errore del critico, per sicurezza non procediamo
            return ""
            
        critique = critic_res["message"].get("content", "")
        
        # --- FASE 3: SINTESI & CONSENSO ---
        synthesizer = AGENT_PROFILES["synthesizer"]
        debate_history = f"PROPOSTA ANALISTA:\n{proposal}\n\nCRITICA DEL RISCHIO:\n{critique}"
        consensus_prompt = get_final_consensus_prompt(debate_history)
        
        logger.info(f"Fase 3: {synthesizer.name} sta elaborando il consenso finale...")
        final_res = self.ollama.chat([
            {"role": "system", "content": synthesizer.system_prompt},
            {"role": "user", "content": consensus_prompt}
        ])
        
        if final_res.get("ok"):
            final_content = final_res["message"].get("content", "")
            logger.info("Ciclo MAD completato con successo.")
            return final_content
            
        return ""

    def simulate_trade_dry_run(self, proposal: str) -> bool:
        """
        [FUTURE] Simulazione via codice prima del consolidamento della regola.
        """
        return True
