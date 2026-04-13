#!/usr/bin/env python3
# main.py
# 2026-04-12 - QUANTUM HUNTER v8.1 (NEURAL SINGULARITY)
"""
AI Trader  Versione Autonoma Neurale (Brain-Driven).
Utilizza il BrainAgent e la SuperMemory per l'evoluzione autonoma.
Capace di apprendere dai fallimenti e adattare la strategia in tempo reale.
"""

import sys
import time
import signal
import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path

# Fix encoding per Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Aggiungi src al path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ai_trader.config.settings import get_settings
from ai_trader.logging.jsonl_logger import get_logger
from ai_trader.exchange.binance_adapter import BinanceAdapter
from ai_trader.strategy.hunter_agent import HunterAgent
from ai_trader.analysis.market_analyzer import MarketAnalyzer
from ai_trader.strategy.grid_engine import GridEngine, GridConfig
from ai_trader.memory.dream_agent import DreamAgent
from ai_trader.memory.episode_store import EpisodeStore
from ai_trader.memory.lesson_store import LessonStore
from ai_trader.brain.brain_agent import BrainAgent
from ai_trader.brain.evolution_engine import EvolutionEngine
from ai_trader.strategy.sentinel import Sentinel
from ai_trader.risk.paladin_agent import PaladinAgent

logger = get_logger("main")
_running = True

def signal_handler(sig, frame):
    global _running
    _running = False

signal.signal(signal.SIGINT, signal_handler)

def auto_configure_grid(analyzer, symbol, budget, num_levels):
    # --- SNIPER MODE v8.3.4 ---
    if budget < 15:
        num_levels = 1
        
    analysis = analyzer.analyze(symbol)
    if not analysis.ok: return None
    price = analysis.price
    atr = analysis.atr
    if atr <= 0 or price <= 0: return None
    margin = atr * 1.5 
    lower = round(price - margin, 8)
    upper = round(price + margin, 8)
    return GridConfig(symbol=symbol, lower_price=lower, upper_price=upper, num_levels=num_levels, budget_usdt=budget)

def execute_grid_action(adapter, grid_engine, action, mode, episode_store):
    symbol = action["symbol"]
    action_type = action["action"]
    try:
        qty = action.get("usdt_amount") if action_type == "BUY" else action["quantity"]
        
        # --- BALANCE GUARD v8.4.2 ---
        if action_type == "SELL":
            snapshot = adapter.get_account_snapshot()
            base_asset = symbol.replace("EUR", "").replace("USDT", "") 
            balances = snapshot.get("balances", [])
            asset_bal = next((b for b in balances if b["asset"] == base_asset), None)
            available = float(asset_bal["free"]) if asset_bal else 0
            
            if available < qty:
                if available > 0:
                    logger.warning(f"Balance Guard: Quantit corretta da {qty} a {available} per {symbol}")
                    qty = available
                else:
                    logger.error(f"Balance Guard: Saldo {base_asset} assente. Sincronizzazione forzata.")
                    grid_engine.record_sell(symbol, action["level_index"], 0, 0, "FORCE_SYNC_MISSING_ASSET")
                    return
        
        order = adapter.place_market_order(symbol, action_type, qty)
        if order.get("ok"):
            if action_type == "BUY":
                grid_engine.record_buy(symbol, action["level_index"], order["avg_price"], order["executed_qty"], str(order.get("order_id", "")))
            else:
                grid_engine.record_sell(symbol, action["level_index"], order["avg_price"], order["executed_qty"], str(order.get("order_id", "")))
        else:
            err_msg = order.get("error", "Errore Sconosciuto")
            logger.error(f"Esecuzione Fallita {symbol}", error=err_msg)
            # FEEDBACK NEURALE: Registra l'episodio di fallimento per il DreamAgent
            episode_store.append_episode(
                category="trading", 
                kind="execution_failure", 
                payload={
                    "symbol": symbol, 
                    "error": err_msg, 
                    "budget": qty,
                    "message": f"Fallito {action_type} su {symbol}: {err_msg}"
                }
            )
    except Exception as e:
        logger.error(f"Crash Esecuzione {symbol}", error=str(e))

def run_grid_cycle(adapter, analyzer, grid_engine, settings, mode, cycle_count, episode_store, brain, auto_config, current_live_budget):
    now = datetime.now(timezone.utc).isoformat()
    whitelist = auto_config.get("WHITELIST_PAIRS", [])
    quote = settings.QUOTE_CURRENCY
    
    if not whitelist:
        print(f"   [CASH] Portfolio 100% {quote}. Cervello in attesa di scansione...")
        return

    for symbol in whitelist:
        try:
            ticker = adapter.get_ticker_price(symbol)
            if not ticker.get("ok"): continue
            current_price = ticker["price"]
            
            # --- PROTEZIONE STATO MERCATO (Globale) ---
            info = adapter.get_symbol_info(symbol)
            if info.get("status") != "TRADING":
                logger.warning(f"Salto {symbol} - Mercato non operativo", status=info.get("status"))
                continue

            if symbol not in grid_engine.grids:
                num_whitelist = len(whitelist)
                budget_for_symbol = (current_live_budget / num_whitelist) * 0.95
                
                # CONSULTAZIONE BRAIN v8.0
                decision = brain.evaluate_strategy(symbol, budget_for_symbol)
                if not decision["ok"]:
                    logger.info(f"BRAIN BLOCK: {symbol} scartato. Ragione: {decision['reason']}")
                    continue

                config = auto_configure_grid(analyzer, symbol, budget_for_symbol, settings.GRID_LEVELS)
                if config:
                    logger.info(f"Grid: Configurazione corretta per {symbol}")
                    grid_engine.setup_grid(config)

            actions = grid_engine.evaluate(symbol, current_price)
            for action in actions:
                execute_grid_action(adapter, grid_engine, action, mode, episode_store)
            
            status = grid_engine.get_status(symbol)
            print(f"   {symbol} | {current_price:.6f} | P&L: {status.get('total_profit', 0):.4f} {quote}")

        except Exception as e:
            logger.error(f"Errore {symbol}", error=str(e))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="mainnet")
    parser.add_argument("--interval", type=float, default=60)
    args = parser.parse_args()
    settings = get_settings()
    mode = args.mode
    interval = args.interval
    quote = settings.QUOTE_CURRENCY

    # Inizializzazione Core
    adapter = BinanceAdapter(mode=mode)
    analyzer = MarketAnalyzer(exchange_adapter=adapter)
    hunter = HunterAgent(adapter, analyzer)
    grid_engine = GridEngine(data_dir=settings.DATA_DIR / "grids")
    episode_store = EpisodeStore()
    lessons = LessonStore()
    
    # Inizializzazione Neural Layer
    brain = BrainAgent(lessons=lessons)
    evolution = EvolutionEngine(settings.AUTONOMOUS_CONFIG_PATH)
    dream_agent = DreamAgent(episodes=episode_store, lessons=lessons)
    sentinel = Sentinel(episode_store=episode_store)
    paladin = PaladinAgent(adapter=adapter, episode_store=episode_store)
    
    last_audit_time = 0
    cycle_count = 1  # 2026-04-12 - Inizia dal primo ciclo
    global_capital_snapshot = 0
    
    while _running:
        auto_config = settings.load_autonomous_config()
        cycle_count += 1
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # AUDIT & NEURAL RESET (v8.1)
        if (time.time() - last_audit_time) > 900 or cycle_count == 1:
            logger.info("AUDIT v8.5: Sincronizzazione Neurale e Intelligence...")
            
            # --- SENTINEL UPDATE v8.5 ---
            try:
                current_whitelist = auto_config.get("WHITELIST_PAIRS", [])
                sentinel.update_intelligence(current_whitelist)
            except Exception as e:
                logger.warning(f"Sentinel: Errore aggiornamento intelligence: {e}")
            
            snapshot = adapter.get_account_snapshot()
            balances = snapshot.get("balances", [])
            total_quote_value = 0
            existing_assets = []
            
            for b in balances:
                asset = b['asset']
                qty = float(b['free']) + float(b['locked'])
                if asset == quote:
                    total_quote_value += float(b['free'])
                    continue
                if asset in ['BNB'] or qty == 0: continue
                
                symbol = asset + quote
                p_res = adapter.get_ticker_price(symbol)
                if p_res.get("ok"):
                    val = qty * p_res["price"]
                    total_quote_value += val
                    if val > 1.0:
                        analysis = analyzer.investigate_deeply(symbol)
                        existing_assets.append({"symbol": symbol, "qty": qty, "val": val, "score": analysis["survival_score"]})

            global_capital_snapshot = total_quote_value
            max_symbols = 1 if total_quote_value < 25 else 2
            
            # Caccia Brain-Guided
            # scansione profonda: Top 50 invece di Top 5 per budget ridotto
            preys = hunter.identify_opportunities(top_n=50, budget=total_quote_value)
            
            final_whitelist = []
            used_slots = 0
            
            # 1. Mantieni o Pulisci Asset Esistenti
            for item in existing_assets:
                if item["score"] < 55:
                    print(f"   PURGE: Liquidazione {item['symbol']} (Score {item['score']})")
                    adapter.place_market_order(item["symbol"], "SELL", item["qty"])
                elif used_slots < max_symbols:
                    final_whitelist.append(item["symbol"])
                    used_slots += 1

            # 2. Identifica candidati (Prede + Whitelist Corrente)
            current_whitelist = auto_config.get("WHITELIST_PAIRS", [])
            target_candidates = {p["symbol"]: p for p in preys}
            
            # Assicura che i simboli in whitelist siano valutati anche se non sono 'prede'
            for sym in current_whitelist:
                if sym not in target_candidates:
                    target_candidates[sym] = {"symbol": sym, "reason": "Whitelist Lock"}

            # 3. Valuta i candidati approvati dal Cervello
            for symbol, p_data in target_candidates.items():
                if used_slots >= max_symbols: break
                
                # --- PROTEZIONE STATUS MERCATO (Audit) ---
                info = adapter.get_symbol_info(symbol)
                if info.get("status") != "TRADING":
                    logger.warning(f"Audit: Scartato {symbol} - Mercato non operativo")
                    continue
                
                if symbol not in final_whitelist:
                    decision = brain.evaluate_strategy(symbol, total_quote_value, p_data)
                    
                    # REGISTRAZIONE NEURALE: Il bot salva il suo ragionamento su SuperMemory
                    episode_store.append_episode(
                        category="trading",
                        kind="brain_decision",
                        payload={
                            "symbol": symbol, 
                            "decision": "APPROVE" if decision["ok"] else "REJECT",
                            "reason": decision["reason"],
                            "budget": total_quote_value
                        },
                        tags=["brain", "decision", symbol]
                    )

                    if decision["ok"]:
                        final_whitelist.append(symbol)
                        used_slots += 1
                    else:
                        logger.warning(f"BRAIN REJECT (Audit): {symbol} - {decision['reason']}")

            # Aggiornamento Evolutivo
            with open(settings.AUTONOMOUS_CONFIG_PATH, "r") as f:
                conf = json.load(f)
            conf["WHITELIST_PAIRS"] = final_whitelist
            with open(settings.AUTONOMOUS_CONFIG_PATH, "w") as f:
                json.dump(conf, f, indent=4)
            
            last_audit_time = time.time()
            logger.info(f"Configurazione Neurale v8.1 ({quote}): {', '.join(final_whitelist)}")

        # Esecuzione Ciclo
        try:
            # --- PALADIN GUARDIAN CHECK v1.0 ---
            health = paladin.check_portfolio_health()
            if health["status"] == "EMERGENCY":
                logger.critical("!!! PALADIN EMERGENCY TRIGGERED !!! Looping stopped for safety.")
                break # Ferma il bot in caso di emergenza capital
            
            logger.info(f"v8.5 'Neural' Cycle #{cycle_count} START")
            run_grid_cycle(adapter, analyzer, grid_engine, settings, mode, cycle_count, episode_store, brain, auto_config, global_capital_snapshot)
            
            if cycle_count % 10 == 0:
                logger.info("AI DREAM: Inizio ciclo di riflessione e apprendimento...")
                dream_agent.run_dream_cycle()
                
                # --- AUTO-EVOLUZIONE CODICE v9.0 ---
                logger.info("EVOLUTION: Controllo lezioni per auto-ottimizzazione...")
                evolution.evolve_from_lessons(category="trading")
                
                brain._load_rules()
                
        except Exception as e:
            logger.error(f"Errore Loop: {e}")
            
        time.sleep(interval)

if __name__ == "__main__":
    main()
