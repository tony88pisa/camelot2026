
import sys
from pathlib import Path

# Aggiungi la cartella 'src' al path
sys.path.insert(0, str(Path.cwd() / "src"))

from ai_trader.api.binance_adapter import BinanceTestnetAdapter
from ai_trader.config.settings import Settings

def check():
    settings = Settings()
    adapter = BinanceTestnetAdapter(settings.BINANCE_API_KEY, settings.BINANCE_API_SECRET)

    print("="*60)
    print("  AUDIT ORDINI REALI - BINANCE TESTNET SERVER")
    print("="*60)

    for symbol in ['DOGEUSDT', 'XRPUSDT']:
        res = adapter.get_open_orders(symbol)
        print(f"\n[COPPIA: {symbol}]")
        if res.get('ok'):
            orders = res.get('orders', [])
            if orders:
                for o in orders:
                    print(f" >> ORDINE #{o['orderId']} | {o['side']} | Prezzo: {o['price']} | Status: {o['status']}")
            else:
                print(" >> Nessun ordine aperto. Il bot  in modalit 'Watching' (attesa target).")
        else:
            print(f" >> Errore API: {res.get('error')}")
    
    print("\n" + "="*60)
    print(" NOTA: Se non vedi ordini, significa che i target di prezzo della griglia")
    print(" non sono ancora stati toccati dal prezzo attuale di Binance.")
    print("="*60)

if __name__ == "__main__":
    check()
