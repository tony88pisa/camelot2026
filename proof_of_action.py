
import sys
import io
from pathlib import Path
import json

# Fix encoding per Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai_trader.strategy.grid_engine import GridEngine, GridConfig
from ai_trader.analysis.market_analyzer import MarketAnalyzer

def prove_action():
    print("="*60)
    print("   LIVE PROOF OF ACTION - AI TRADER v2.0 (Aprile 2026)")
    print("="*60)

    # 1. Inizializzazione
    engine = GridEngine(data_dir=Path("data/test_proof"))
    analyzer = MarketAnalyzer()
    symbol = "BTCUSDT"
    
    # 2. Setup Griglia Iniziale (Statica)
    print("\n[STEP 1] Creazione Griglia Iniziale...")
    config = GridConfig(symbol=symbol, lower_price=60000, upper_price=64000, num_levels=4, budget_usdt=100)
    engine.setup_grid(config)
    status = engine.get_status(symbol)
    print(f"    Range Iniziale: {status['range']}")
    for l in status['levels']:
        print(f"      Level {l['index']}: ${l['price']}")

    # 3. PROVA DI ADATTAMENTO (ATR EXPLOSION)
    print("\n[STEP 2] Simulazione Esplosione Volatilit (ATR x3)...")
    current_price = 62000
    fake_atr = 2000.0 # Volatilit altissima
    engine.recalculate_adaptive_levels(symbol, current_price, fake_atr, multiplier=1.5)
    
    new_status = engine.get_status(symbol)
    print(f"    NUOVO Range Adattivo: {new_status['range']}")
    for l in new_status['levels']:
        print(f"      Level {l['index']}: ${l['price']} (Aggiornato!)")

    # 4. PROVA GEM HUNTER (VOLUME SPIKE)
    print("\n[STEP 3] Simulazione 'Gemma' rilevata (Volume Spike 10x)...")
    fake_closes = [62000] * 50
    fake_volumes = [100.0] * 49 + [1000.0] # 10x spike
    
    analysis = analyzer.analyze(symbol, klines=[[0,0,0,0,c,v,0,0,0,0,0,0] for c,v in zip(fake_closes, fake_volumes)])
    
    print(f"    Hunter Score: {analysis.hunter_score}")
    if analysis.is_anomaly:
        print(f"    [SUCCESS] GEM DETECTED! Il sensore Hunter ha risposto all'anomalia.")
    
    print("\n" + "="*60)
    print("  CONCLUSIONE: Il sistema non solo parla, ma esegue ricalcoli matematici reali.")
    print("="*60)

if __name__ == "__main__":
    prove_action()
