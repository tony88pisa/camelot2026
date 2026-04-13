import sys
from pathlib import Path

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai_trader.memory.lesson_store import LessonStore

def seed_wisdom():
    store = LessonStore()
    title = "Vincoli Budget Binance EUR 2026"
    content = """
    # Lezione Strategica: Gestione Budget Ridotto (EUR)
    
    REGOLA: Con un budget totale inferiore a 10.50 EUR, evitare coppie istituzionali come ETHAEUR o BTCEUR. 
    
    MOTIIVAZIONE: Questi mercati spesso richiedono un minimo di 10.00 EUR per l'apertura ordini. 
    
    AZIONE: Prediligere mercati entry-level (5 EUR min) come SOLEUR o micro-cap (1 EUR min) come PEPEEUR o DOGEEUR per garantire la piena operativit della griglia.
    """
    
    filename = store.append_lesson(
        category='trading', 
        title=title, 
        content=content, 
        tags=['budget', 'eur', 'instruction', 'neural_start']
    )
    if filename:
        print(f"Saggezza impressa con successo nel file: {filename}")
    else:
        print("Errore durante l'imprinting neurale.")

if __name__ == "__main__":
    seed_wisdom()
