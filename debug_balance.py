import sys
import io
from pathlib import Path

# Forza l'output in UTF-8 per evitare errori su Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai_trader.exchange.binance_testnet_adapter import BinanceTestnetAdapter
from ai_trader.config.settings import get_settings

def check():
    s = get_settings()
    a = BinanceTestnetAdapter(
        s.BINANCE_TESTNET_BASE_URL, 
        s.BINANCE_TESTNET_API_KEY, 
        s.BINANCE_TESTNET_API_SECRET
    )
    
    print("--- DATA_DUMP_START ---")
    res = a.get_account_snapshot()
    
    if not res.get("ok"):
        print(f"ERROR: {res.get('error')}")
        return

    balances = res.get("balances", [])
    
    for b in balances:
        asset = b['asset']
        free = float(b['free'])
        locked = float(b['locked'])
        if (free + locked) > 0:
            print(f"ASSET:{asset}|FREE:{free}|LOCKED:{locked}")

    print("--- DATA_DUMP_END ---")

if __name__ == "__main__":
    check()
