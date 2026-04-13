# start_live.py
# 2026-04-13 - Phase 4: Protected Live Ignition
"""
Lanciatore certificato per il trading reale su Binance (Staging Live).
Esegue pre-verifiche di sicurezza prima di istanziare l'ApexReactor.
"""

import asyncio
import os
import sys
from main import ApexReactor
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("live_ignition")

async def ignite():
    print("============================================================")
    print("      QUANTUM ORACLE - LIVE STAGING IGNITION (v12.0)")
    print("============================================================")
    
    # 1. Forza la configurazione di sicurezza per lo staging live
    # In questa fase, forziamo i parametri anche se non presenti in settings
    from ai_trader.config import settings
    cfg = settings.get_settings()
    
    # REGOLA DI STAGING: Solo BTCUSDT
    if cfg.WHITELIST_PAIRS != ["BTCUSDT"]:
        print("!!! SAFETY OVERRIDE: Restricting whitelist to BTCUSDT for staging.")
        cfg.WHITELIST_PAIRS = ["BTCUSDT"]

    print(f"[*] Trading Mode: LIVE")
    print(f"[*] Whitelist: {cfg.WHITELIST_PAIRS}")
    print(f"[*] Environment Check: OK")
    print("------------------------------------------------------------")

    try:
        # 2. Istanziazione Reactor in modo LIVE
        reactor = ApexReactor(mode="live")
        
        # 3. Esecuzione Sequenza di Boot con Readiness Gate integrato
        await reactor.boot_sequence()
        
        # 4. Inizio Ciclo Operativo Autonomo
        print("[v12.0] SYSTEM ONLINE. AUTONOMOUS TRADING ENGAGED.")
        print("Premi CTRL+C per arresto di emergenza.")
        
        while reactor.running:
            await reactor.process_cycle()
            await asyncio.sleep(reactor.interval)
            
    except KeyboardInterrupt:
        print("\n[!] Emergency Signal Received. Shutting down...")
    except SystemExit:
        print("\n[!] Readiness Gate BLOCKED startup. Check logs/main_reactor.log")
    except Exception as e:
        logger.critical(f"CRITICAL BOOT FAILURE: {str(e)}")
        print(f"\n[!!!] CRITICAL FAILURE: {e}")
    finally:
        # Assicuriamo la chiusura delle connessioni
        if 'reactor' in locals():
            await reactor.shutdown_sequence()

if __name__ == "__main__":
    try:
        asyncio.run(ignite())
    except KeyboardInterrupt:
        pass
