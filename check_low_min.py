import sys
from pathlib import Path

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai_trader.exchange.binance_adapter import BinanceAdapter

def check_low_min_eur():
    adapter = BinanceAdapter(mode="mainnet")
    info = adapter._request("GET", "/api/v3/exchangeInfo")
    
    if "_error_internal" in info:
        print(f"Errore: {info['_error_internal']}")
        return

    eur_pairs = [s for s in info['symbols'] if s['symbol'].endswith('EUR') and s['status'] == 'TRADING']
    
    print("\n--- ANALISI MERCATI COMPATIBILI (BUDGET 9.58 EUR) ---")
    budget = 9.58
    for p in eur_pairs:
        symbol = p['symbol']
        # Estrai il valore minimo dell'ordine (Notional Filter)
        notional_filter = next((f for f in p.get('filters', []) if f['filterType'] in ['NOTIONAL', 'MIN_NOTIONAL']), None)
        
        if notional_filter:
            min_val = float(notional_filter.get('minNotional', 10.0))
            if budget >= min_val:
                print(f"[OK] {symbol} - Minimo: {min_val} EUR")
            elif symbol == "ETHAEUR":
                print(f"[BLOCCATO] {symbol} - Minimo: {min_val} EUR")

if __name__ == "__main__":
    check_low_min_eur()
