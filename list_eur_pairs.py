import sys
from pathlib import Path

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai_trader.exchange.binance_adapter import BinanceAdapter

def list_eur_pairs():
    adapter = BinanceAdapter(mode="mainnet")
    info = adapter._request("GET", "/api/v3/exchangeInfo")
    
    if "_error_internal" in info:
        print(f"Errore: {info['_error_internal']}")
        return

    eur_pairs = [s for s in info['symbols'] if s['symbol'].endswith('EUR') and s['status'] == 'TRADING']
    
    print(f"\n--- MERCATI EUR DISPONIBILI ({len(eur_pairs)}) ---")
    # Mostriamo i principali per volumi o utilit
    major_coins = ['BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'DOT', 'DOGE', 'SHIB', 'PEPE', 'FDUSD', 'USDC']
    for p in eur_pairs:
        symbol = p['symbol']
        base = p['baseAsset']
        
        # Filtro per le pi note
        if base in major_coins or len(eur_pairs) < 20:
            # Trova il MIN_NOTIONAL (minimo ordine)
            min_notional = next((f['minNotional'] for f in p.get('filters', []) if f['filterType'] == 'MIN_NOTIONAL'), "N/A")
            print(f"Coppia: {symbol} | Minimo Ordine: {min_notional} EUR")

if __name__ == "__main__":
    list_eur_pairs()
