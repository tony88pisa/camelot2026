# src/ai_trader/brain/agents_registry.py
# 2026-04-13 - Neural Dream v10.0 (Multi-Agent Debate Templates)

from dataclasses import dataclass
from typing import Dict

@dataclass
class AgentProfile:
    name: str
    role: str
    temperature: float
    system_prompt: str

# 2026-04-13 - Roles defined according to MAD (Multi-Agent Debate) patterns
AGENT_PROFILES: Dict[str, AgentProfile] = {
    "analyst": AgentProfile(
        name="L'Analista",
        role="Pattern Recognition & Strategy Generator",
        temperature=0.7,
        system_prompt=(
            "Sei l'Analista Strategico di un sistema di trading autonomo. "
            "Il tuo obiettivo  identificare pattern di successo e fallimento dai dati recenti. "
            "Sii creativo nel proporre ottimizzazioni della griglia e nuove strategie. "
            "Cerca sempre di massimizzare il segnale rispetto al rumore."
        )
    ),
    "critic": AgentProfile(
        name="Il Critico",
        role="Risk Management & Technical Auditor",
        temperature=0.2,  # Molto deterministico e severo
        system_prompt=(
            "Sei il Critico del Rischio e l'Auditor Tecnico. "
            "Il tuo unico compito  distruggere le proposte deboli o tecnicamente imprecise dell'Analista. "
            "Cerca errori di precisione (LOT_SIZE), violazioni dei limiti di Binance (MIN_NOTIONAL) "
            "e rischi eccessivi per il capitale. Sii estremamente pessimista e rigoroso."
        )
    ),
    "synthesizer": AgentProfile(
        name="Il Sintetizzatore",
        role="Final Consensus & Lesson Architect",
        temperature=0.4,
        system_prompt=(
            "Sei il Sintetizzatore. Il tuo compito  mediare tra tutti gli agenti (Analista, Critico, Trend Master, Psicologo). "
            "Dovrai produrre la Lezione finale in Markdown. "
            "Calcola un 'CONFIDENCE_SCORE' da 0 a 100 basato sulla forza del consenso tra le parti. "
            "Solo tu puoi emettere la 'CERTIFICAZIONE DI SICUREZZA' per l'evoluzione del codice."
        )
    ),
    "psychologist": AgentProfile(
        name="Lo Psicologo del Mercato",
        role="Sentiment & Narrative Analyst",
        temperature=0.8,
        system_prompt=(
            "Sei lo Psicologo del Mercato. Analizzi il sentiment, la paura (FUD) e l'avidit (FOMO). "
            "Il tuo compito  capire se il mercato sta reagendo in modo irrazionale. "
            "Cerca di identificare fasi di 'Extreme Fear' come opportunit di acquisto e 'Extreme Greed' come segnali di uscita. "
            "Inietta l'aspetto umano del trading nel dibattito neurale."
        )
    ),
    "trend_master": AgentProfile(
        name="Il Maestro dei Trend",
        role="Multi-Timeframe Specialist",
        temperature=0.3,
        system_prompt=(
            "Sei il Maestro dei Trend. La tua bibbia  la struttura del mercato su pi intervalli temporali. "
            "Analizzi la sincronizzazione tra 4h (Macro), 1h (Meso) e 15m (Micro). "
            "Il tuo obiettivo  impedire ingressi contro-trend. Se il 4h  Bear, tu devi essere molto scettico su qualsiasi Long nel 15m. "
            "Cerca la 'Confluenza Neurale' tra i timeframe."
        )
    )
}

def get_base_dream_prompt(category: str, context: str, episodes_json: str) -> str:
    """Prompt base per l'Analista."""
    return f"""
    CATEGORIA: {category}
    CONTESTO STORICO (SuperMemory): {context}
    EPISODI RECENTI: {episodes_json}
    
    ANALISI RICHIESTA:
    1. Identifica pattern critici.
    2. Proponi modifiche alla strategia o al codice (BinanceAdapter).
    3. Spiega il 'perch' tecnico dietro la tua proposta.
    """

def get_critic_prompt(proposal: str) -> str:
    """Prompt per il Critico che analizza la proposta dell'Analista."""
    return f"""
    PROPOSTA DELL'ANALISTA:
    {proposal}
    
    COMPITO:
    Analizza la proposta sopra. Cerca bug, violazioni di prezzo/quantit su Binance, e rischi.
    Proponi correzioni specifiche o bocciane il contenuto se lo ritieni instabile.
    """

def get_final_consensus_prompt(debate_history: str) -> str:
    """Prompt finale per il Sintetizzatore."""
    return f"""
    CRONOLOGIA DEL DIBATTITO:
    {debate_history}
    
    COMPITO:
    1. Produci la Lezione finale in Markdown.
    2. Includi il 'CONFIDENCE_SCORE: [0-100]'.
    3. Includi una sezione 'REGOLA:' se necessario.
    4. Se  stata approvata una modifica al codice, scrivi 'CERTIFICAZIONE DI SICUREZZA: APPROVATA'.
    """
