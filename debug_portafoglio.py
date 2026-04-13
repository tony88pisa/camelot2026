import sys
from pathlib import Path
import json

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai_trader.exchange.binance_adapter import BinanceAdapter

def raw_check():
    adapter = BinanceAdapter(mode="mainnet")
    # Vediamo prima se le chiavi funzionano
    time_res = adapter.get_server_time()
    print(f"Sincronizzazione Server: {time_res}")
    
    snapshot = adapter.get_account_snapshot()
    
    if "_error_internal" in snapshot:
        print(f"\n ERRORE API: {snapshot['_error_internal']}")
        return

    print("\n--- RISPOSTA GREZZA BINANCE (SOLO ASSET > 0) ---")
    balances = snapshot.get("balances", [])
    found = False
    for b in balances:
        if float(b['free']) > 0 or float(b['locked']) > 0:
            found = True
            print(json.dumps(b, indent=2))
            
    if not found:
        print("Binance riporta: TUTTI I SALDI SONO A ZERO.")

if __name__ == "__main__":
    raw_check()
