# check_api.py
import os
import sys
from pathlib import Path

# Aggiungi la root del progetto al path
src_path = Path("h:/ai trader/Ai trader/src")
sys.path.append(str(src_path))

from ai_trader.exchange.binance_adapter import BinanceAdapter

def check():
    print("--- Diagnostica Profonda Quantum Hunter ---")
    try:
        adapter = BinanceAdapter(mode="mainnet")
        health = adapter.health_check()
        print(f"Trading Abilitato: {health.get('private_endpoints_available')}")
        
        snapshot = adapter.get_account_snapshot()
        if "_error_internal" in snapshot:
            print(f"Errore API: {snapshot['_error_internal']}")
            return

        balances = snapshot.get("balances", [])
        print("\n--- Portafoglio SPOT Rilevato ---")
        found_any = False
        for b in balances:
            free = float(b['free'])
            locked = float(b['locked'])
            if free > 0 or locked > 0:
                print(f"Asset: {b['asset']} | Libero: {free} | In ordine: {locked}")
                found_any = True
        
        if not found_any:
            print("Il portafoglio SPOT risulta completamente vuoto (0.00).")
            print("Controlla se i fondi sono in: Finanziamento, Guadagno (Earn) o Future.")
            
    except Exception as e:
        print(f"Errore critico: {e}")

if __name__ == "__main__":
    check()
