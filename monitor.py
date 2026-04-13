# monitor.py
# 2026-04-12 - Quantum Terminal Monitor v5.5 - Absolute Autonomy Edition
import json
import os
import time
import sys
from pathlib import Path
from datetime import datetime

# Colori ANSI per terminale Windows (Cyber Theme)
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BG_BLUE = '\033[44m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def format_currency(value):
    color = Colors.GREEN if value >= 0 else Colors.RED
    return f"{color}{value:+.4f} USDT{Colors.END}"

def get_risk_bar(score):
    """Genera una barra di rischio dinamica."""
    bar_length = 10
    filled = int(score)
    empty = bar_length - filled
    char = ""
    color = Colors.GREEN if score < 4 else Colors.YELLOW if score < 7 else Colors.RED
    return f"[{color}{char*filled}{Colors.END}{''*empty}] {score}/10"

def draw_monitor():
    state_path = Path("data/grids/grid_state.json")
    config_path = Path("data/autonomous_config.json")
    
    # Caricamento Dati
    try:
        data = {}
        if state_path.exists():
            with open(state_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
    except:
        print("Recupero dati in corso...")
        return

    clear_screen()
    now = datetime.now().strftime("%H:%M:%S")
    
    # --- HEADER ---
    print(f"{Colors.BOLD}{Colors.BG_BLUE}  QUANTUM_TERMINAL_V5.5 // MISSION_CONTROL // {now}  {Colors.END}")
    
    # --- ORACLE SECTION ---
    mode = config.get("MARKET_MODE", "UNKNOWN")
    mode_color = Colors.RED if mode == "WAR_HEDGE" else Colors.GREEN if mode == "RECOVERY" else Colors.CYAN
    risk_score = config.get("risk_score", 5)
    
    print(f"\n{Colors.BOLD} VISIONE ORACOLARE:{Colors.END}")
    print(f"   Modalit Strategica: {mode_color}{Colors.BOLD}{mode}{Colors.END}")
    print(f"   Indice Rischio Globale: {get_risk_bar(risk_score)}")
    
    # --- BUDGET ISOLATO SECTION ---
    starting_budget = 50.0
    total_profit = sum(g.get("total_profit", 0) for g in data.values())
    current_equity = starting_budget + total_profit
    
    print(f"\n{Colors.BOLD} CAPITALE PROGETTO 50:{Colors.END}")
    print(f"   Equity Attuale:  {Colors.BOLD}${current_equity:,.2f}{Colors.END}")
    print(f"   Profitto Netto:  {format_currency(total_profit)}")
    
    # --- MARKETS SECTION ---
    print(f"\n{Colors.BOLD} RADAR MERCATI ATTIVI:{Colors.END}")
    if not data:
        print("   In attesa di dati dal fronte...")
    else:
        for symbol, grid in data.items():
            active = grid.get("active", False)
            status_icon = f"{Colors.GREEN}{Colors.END}" if active else f"{Colors.RED}{Colors.END}"
            levels = grid.get("levels", [])
            bought = len([l for l in levels if l.get("status") == "bought"])
            total = len(levels)
            
            pnl = grid.get("total_profit", 0)
            print(f"   {status_icon} {Colors.BOLD}{symbol:<10}{Colors.END} | Griglia: {bought}/{total} | PnL: {format_currency(pnl)}")

    # --- RECENT EVOLUTION ---
    evo_log_path = Path("data/evolution_log.jsonl")
    if evo_log_path.exists():
        print(f"\n{Colors.BOLD} ULTIMA EVOLUZIONE:{Colors.END}")
        try:
            with open(evo_log_path, "r") as f:
                last_line = f.readlines()[-1]
                ev = json.loads(last_line)
                print(f"   {Colors.YELLOW}> {ev.get('change')} ({ev.get('new')}){Colors.END}")
        except: pass

    print(f"\n{Colors.CYAN}{'='*50}{Colors.END}")
    print(f"{Colors.BOLD}Premi CTRL+C per chiudere la sessione di comando.{Colors.END}")

def main():
    try:
        while True:
            draw_monitor()
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n\n Sessione di monitoraggio chiusa. Il bot continua ad operare in background.")
        sys.exit(0)

if __name__ == "__main__":
    main()
