import sys
from pathlib import Path

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai_trader.exchange.binance_adapter import BinanceAdapter

def check_eur_limits():
    adapter = BinanceAdapter(mode="mainnet")
    info = adapter._request("GET", "/api/v3/exchangeInfo")
    
    if "_error_internal" in info:
        print(f"Errore: {info['_error_internal']}")
        return

    eur_pairs = [s for s in info['symbols'] if s['symbol'].endswith('EUR') and s['status'] == 'TRADING']
    
    print(f"\n--- ANALISI LIMITI MERCATO EUR ---")
    my_budget = 9.58
    found_possible = False
    
    for p in eur_pairs:
        symbol = p['symbol']
        # Cerca il filtro NOTIONAL o MIN_NOTIONAL
        notional_filter = next((f for f in p.get('filters', []) if f['filterType'] in ['NOTIONAL', 'MIN_NOTIONAL']), None)
        
        if notional_filter:
            min_val = float(notional_filter.get('minNotional', 10.0))
            if my_budget >= min_val:
                print(f" POSSIBILE: {symbol} (Minimo: {min_val} EUR)")
                found_possible = True
            elif symbol == "ETHAEUR":
                print(f" BLOCCATO: {symbol} (Minimo: {min_val} EUR | Hai: {my_budget} EUR)")

    if not found_possible:
        print("\n ATTENZIONE: Nessun mercato EUR trovato compatibile con il tuo budget attuale di 9.58 EUR.")
        print("Binance solitamente richiede un minimo di 10 EUR per la maggior parte delle coppie.")

if __name__ == "__main__":
    check_eur_limits()
