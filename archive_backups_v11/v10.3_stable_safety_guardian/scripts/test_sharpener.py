# scripts/test_sharpener.py
# 2026-04-13 - Test manuale per il Context Sharpener v10.1

import sys
import os
import json

# Aggiungi la root al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ai_trader.brain.context_sharpener import ContextSharpener

def test_sharpener():
    sharpener = ContextSharpener()
    
    # Mock di episodi (un tecnico e uno news lungo)
    test_episodes = [
        {
            "timestamp": "2026-04-13T10:00:00",
            "symbol": "PEPEEUR",
            "price": 0.000003,
            "rsi": 45.5,
            "kind": "market_analyzer",
            "message": "Analisi tecnica completata con successo per PEPEEUR in regime normal."
        },
        {
            "timestamp": "2026-04-13T10:05:00",
            "kind": "market_news",
            "category": "research",
            "message": "LUNGA NEWS CRITTOGRAFICA: Esperti del settore segnalano che il mercato delle memecoin sta subendo una mutazione strutturale dovuta all'integrazione di sistemi di intelligenza artificiale decentralizzati che operano su scala globale. Questi sistemi, spesso definiti 'Neural Swarms', sono in grado di influenzare la liquidit su Binance in modi mai visti prima, portando a una volatilit estrema che richiede un monitoraggio costante dei livelli di RSI e dei volumi di scambio nelle ultime 24 ore. In particolare PEPE sembra essere al centro di questa tempesta perfetta..."
        }
    ]

    print("--- TEST CONTEXT SHARPENER v10.1 ---")
    print(f"Input: {len(test_episodes)} episodi")
    
    sharpened = sharpener.sharpen_episodes(test_episodes)
    
    print(f"Output: {len(sharpened)} episodi")
    
    for i, ep in enumerate(sharpened):
        print(f"\nEpisodio {i+1} compattato:")
        print(json.dumps(ep, indent=2))
        
        # Verifiche
        if ep.get("price"):
            print("[OK] Dati tecnici PRESERVATI.")
        if ep.get("k") == "news":
            info = ep.get("info", "")
            if "..." in info:
                print(f"[OK] News TRONCATA correttamente ({len(info)} char).")

if __name__ == "__main__":
    test_sharpener()
