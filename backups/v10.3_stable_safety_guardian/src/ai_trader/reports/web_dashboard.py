# src/ai_trader/reports/web_dashboard.py
import json
from pathlib import Path
from datetime import datetime

def generate_html_report(state_path: Path, output_path: Path, market_analyses: dict = None, activity_log: list = None, active_orders: dict = None, balances: list = None, trade_history: dict = None, agents_states: dict = None, oracle_bulletin: str = None, evolution_log: list = None, macro_vision: str = None, market_mode: str = "BALANCED", lessons: list = None, hunter_opportunities: list = None):
    """
    Genera la Quantum Dashboard v6.0 - THE TECHNICAL MENTOR.
    Interfaccia multi-scheda per non-trader con spiegazioni tecniche integrate.
    """
    starting_budget = 32.00 # I tuoi 30 circa
    total_profit = 0.0
    grid_data = {}
    hunter_opportunities = [] # Nuova lista per Hunter v6.5
    
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                grid_data = json.load(f)
                for symbol, data in grid_data.items():
                    total_profit += data.get("total_profit", 0.0)
        except: pass
            
    now = datetime.now().strftime("%H:%M:%S")
    current_virtual_balance = starting_budget + total_profit

    # Colori dinamici in base al Market Mode
    mode_color = "#00ff88"
    if market_mode == "WAR_HEDGE": mode_color = "#ff3333"
    elif market_mode == "DE_RISKING": mode_color = "#ffcc00"

    html = f"""
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum Hub v6.0 - Technical Mentor</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono&family=Inter:wght@400;700;900&display=swap" rel="stylesheet">
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
    <style>
        :root {{
            --bg: #03070f;
            --card: #070d1a;
            --primary: {mode_color};
            --text: #e0e6ed;
            --dim: #8892b0;
            --accent: #5ef1ff;
        }}
        * {{ box-sizing: border-box; }}
        body {{ 
            background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; 
            margin: 0; padding-bottom: 50px; line-height: 1.5;
        }}
        header {{
            background: rgba(3, 7, 15, 0.9); backdrop-filter: blur(12px);
            padding: 15px 40px; border-bottom: 2px solid var(--primary);
            display: flex; justify-content: space-between; align-items: center;
            position: sticky; top: 0; z-index: 1000;
        }}
        .tabs {{ display: flex; gap: 10px; padding: 20px 40px; }}
        .tab-btn {{
            background: #0b1221; border: 1px solid #1a2333; color: var(--dim);
            padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: bold;
            font-family: 'Space Mono'; font-size: 0.8em;
        }}
        .tab-btn.active {{ background: var(--primary); color: #000; border-color: var(--primary); }}
        
        .container {{ display: grid; grid-template-columns: 1fr 340px; gap: 20px; padding: 0 40px; }}
        .pnl-hero {{
            background: linear-gradient(135deg, #0b1221, #03070f); border: 1px solid #1a2333;
            padding: 30px; border-radius: 20px; margin-bottom: 25px;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .card {{ background: var(--card); border-radius: 15px; padding: 20px; border: 1px solid #1a2333; }}
        .section-title {{ 
            font-family: 'Space Mono'; color: var(--primary); font-size: 0.75em; 
            text-transform: uppercase; letter-spacing: 2px; margin-bottom: 15px;
        }}
        .mentor-box {{
            background: rgba(94, 241, 255, 0.05); border-left: 3px solid var(--accent);
            padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 0.85em;
        }}
        .mentor-box b {{ color: var(--accent); display: block; margin-bottom: 5px; text-transform: uppercase; }}

        .grid-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(450px, 1fr)); gap: 20px; }}
        .chart-box {{ height: 380px; border-radius: 12px; overflow: hidden; border: 1px solid #1a2333; margin-top: 10px; }}
        
        .lesson-card {{
            background: #0b1221; padding: 15px; border-radius: 10px; margin-bottom: 15px;
            border-left: 4px solid var(--primary);
        }}
        .hide {{ display: none; }}
        .status-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--primary); margin-right: 8px; box-shadow: 0 0 10px var(--primary); }}
        
        ::-webkit-scrollbar {{ width: 6px; }}
        ::-webkit-scrollbar-thumb {{ background: #1a2333; border-radius: 10px; }}
    </style>
</head>
<body>
    <header>
        <div style="display: flex; align-items: center; gap: 15px;">
            <div style="font-weight: 900; font-size: 1.6em; letter-spacing: 1px;">QUANTUM <span style="color:var(--primary)">HUNTER</span> v6.5</div>
            <div style="background: var(--primary); color: #000; padding: 3px 12px; border-radius: 20px; font-weight: 800; font-size: 0.75em;">{market_mode}</div>
        </div>
        <div style="text-align: right; font-family: 'Space Mono'; font-size: 0.8em; color: var(--dim);">
            <div>ORACLE_SYNC: <span style="color:var(--text)">{now}</span></div>
            <div>STATUS: <span style="color:var(--primary)">READY_FOR_PROFIT</span></div>
        </div>
    </header>

    <div class="tabs">
        <button class="tab-btn active" id="btn-main" onclick="showView('main')"> COMMAND_CENTER</button>
        <button class="tab-btn" id="btn-hunter" onclick="showView('hunter')"> HUNTER_VISION</button>
        <button class="tab-btn" id="btn-lessons" onclick="showView('lessons')"> NEURAL_LIBRARY</button>
    </div>

    <div class="container">
        <!-- VISTA COMMAND CENTER -->
        <div id="view-main">
            <div class="pnl-hero">
                <div>
                    <div style="color: var(--dim); font-size: 0.8em; font-family: 'Space Mono';">EQUITY TOTALE (PORTAFOGLIO)</div>
                    <div style="font-size: 2.8em; font-weight: 900; margin: 5px 0;">{current_virtual_balance:,.2f} $</div>
                    <div style="color: var(--primary); font-family: 'Space Mono'; font-weight: bold; font-size: 1.1em;">
                        PnL LIVE: {total_profit:+.4f} $ ({(total_profit/starting_budget*100):+.2f}%)
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="color: var(--dim); font-size: 0.8em; font-family: 'Space Mono';">CAPITALE PROTETTO</div>
                    <div style="font-size: 1.5em; font-weight: bold;">{starting_budget:,.2f} $</div>
                    <div style="color: var(--accent); font-size: 0.7em; margin-top: 5px;">STRATEGIA: {market_mode}</div>
                </div>
            </div>

            <div class="grid-layout" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                <div class="card">
                    <div class="section-title">SENTENZA DEL GENERALE (AI MACRO)</div>
                    <div style="font-size: 1.22em; font-weight: 700; font-style: italic; color: #fff; line-height: 1.4;">
                        "{macro_vision if macro_vision else "Scansione dei mercati globali in corso..."}"
                    </div>
                    <div style="margin-top: 15px; font-size: 0.8em; color: var(--dim); max-height: 100px; overflow-y: auto; white-space: pre-wrap; line-height: 1.6;">
{oracle_bulletin if oracle_bulletin else "Nessun bollettino rilevante nelle ultime 24 ore."}
                    </div>
                </div>
                <div class="card">
                    <div class="section-title">STATO AGENTI QUANTISTICI</div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div style="background: rgba(30, 40, 60, 0.4); padding: 15px; border-radius: 10px; border-bottom: 4px solid {mode_color};">
                            <div style="font-family: 'Space Mono'; font-size: 0.6em; color: {mode_color};">GENERAL</div>
                            <div style="font-size: 0.85em; font-weight: bold; margin-top: 5px;">"{agents_states.get('oracle', 'OK') if agents_states else 'LIVE'}"</div>
                        </div>
                        <div style="background: rgba(30, 40, 60, 0.4); padding: 15px; border-radius: 10px; border-bottom: 4px solid #ff00ff;">
                            <div style="font-family: 'Space Mono'; font-size: 0.6em; color: #ff00ff;">DREAMER</div>
                            <div style="font-size: 0.85em; font-weight: bold; margin-top: 5px;">"{agents_states.get('dreamer', 'Riposo...') if agents_states else 'READY'}"</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="grid-grid">
            <!-- Griglie dinamiche iniettate qui -->
"""
    if grid_data:
        for i, (symbol, grid) in enumerate(grid_data.items()):
            wid = f"chart_{i}"
            html += f"""
                <div class="card">
                    <div class="section-title"><span class="status-dot"></span>RADAR LIVE: {symbol}</div>
                    <div class="chart-box" id="{wid}"></div>
                    <script type="text/javascript">
                    new TradingView.widget({{
                        "autosize": true, "symbol": "BINANCE:{symbol}", "interval": "15",
                        "theme": "dark", "style": "1", "locale": "it", "hide_top_toolbar": true, "container_id": "{wid}"
                    }});
                    </script>
                    <div style="margin-top: 15px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; border-top: 1px solid #1a2333; padding-top: 15px;">
                        <div style="text-align: center;">
                            <div style="color: var(--dim); font-size: 0.6em; font-family: 'Space Mono';">PnL ASSET</div>
                            <div style="font-weight: 900; font-size: 0.9em; color: var(--primary);">{grid.get('total_profit', 0):+.4f} $</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="color: var(--dim); font-size: 0.6em; font-family: 'Space Mono';">BUY_ORDERS</div>
                            <div style="font-weight: 900; font-size: 0.9em; color: var(--accent);">{len(grid.get('buy_levels', []))}</div>
                        </div>
                        <div style="text-align: center;">
                            <div style="color: var(--dim); font-size: 0.6em; font-family: 'Space Mono';">LIVE_PRICE</div>
                            <div style="font-weight: 900; font-size: 0.9em;">{grid.get('current_price', 0):,.2f}</div>
                        </div>
                    </div>
                </div>
            """
    else:
        html += '<div class="card"><div style="color: var(--dim); text-align: center; padding: 40px;">Nessuna griglia attiva. In attesa di ordini dall\'Oracolo...</div></div>'

    html += """
            </div>
        </div>

        <!-- VISTA HUNTER VISION (v6.5) -->
        <div id="view-hunter" class="hide">
            <div class="card">
                <div class="section-title">OCCHI DEL CACCIATORE: TOP OPPORTUNITIES</div>
                <div style="margin-bottom: 20px; color: var(--dim); font-size: 0.9em;">
                    L'AI sta scansionando i Top 20 mercati per volume. Le monete qui sotto sono candidate per l'allocazione dinamica dei tuoi 30.
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px;">
"""
    if hunter_opportunities:
        for opt in hunter_opportunities:
            score_color = "#00ff88" if opt.get('hunter_score', 0) > 0.7 else "#ffcc00"
            html += f"""
                    <div class="lesson-card" style="border-left-color: {score_color};">
                        <div style="display: flex; justify-content: space-between;">
                            <div style="font-weight: 900; color: {score_color}; font-family: 'Space Mono';">SCORE: {opt.get('hunter_score', 0):.2f}</div>
                            <div style="font-size: 0.7em; color: var(--dim);">RSI: {opt.get('rsi', 0)}</div>
                        </div>
                        <div style="font-size: 1.35em; font-weight: 900; margin: 10px 0; color: #fff;">{opt.get('symbol')}</div>
                        <div style="font-size: 0.8em; color: var(--dim);">REC: <b style="color:var(--text)">{opt.get('recommendation')}</b></div>
                        <div style="font-size: 0.8em; color: var(--dim); margin-top: 5px;">Opportunit rilevata nei Top 20 mercati.</div>
                    </div>
            """
    else:
        html += """
                    <div class="lesson-card" style="border-left-color: var(--accent);">
                        <div style="font-weight: 900; color: var(--accent); font-family: 'Space Mono';">HUNTER_SCAN: ACTIVE</div>
                        <div style="font-size: 1.1em; font-weight: bold; margin: 10px 0;">Nessun target critico...</div>
                        <div style="font-size: 0.8em; color: var(--dim);">Il cacciatore sta monitorando i flussi volumetrici alla ricerca di un segnale forte.</div>
                    </div>
        """
    html += """
                </div>
            </div>
        </div>

        <!-- VISTA NEURAL LIBRARY -->
        <div id="view-lessons" class="hide">
            <div class="card">
                <div class="section-title">BIBLIOTECA DELLA CONOSCENZA (NEURAL LIBRARY)</div>
                <div style="margin-bottom: 20px; color: var(--dim); font-size: 0.9em;">
                    Qui sono archiviate le lezioni che l'AI ha appreso dal mercato. Ogni lezione ha modificato la strategia che vedi applicata oggi.
                </div>
"""
    if lessons:
        for l in lessons[:10]:
            html += f"""
                <div class="lesson-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <div style="color: var(--primary); font-weight: 900; font-family: 'Space Mono';">LES_ID: {l.get('id', 'N/A')}</div>
                        <div style="font-size: 0.75em; color: var(--dim);">{l.get('date', '')[:16]}</div>
                    </div>
                    <div style="font-size: 0.95em; font-weight: bold; color: #fff;">{l.get('title', 'Lezione AI')}</div>
                </div>
            """
    else:
        html += '<div style="color: var(--dim); text-align: center; padding: 40px;">L\'AI non ha ancora completato il suo primo ciclo di apprendimento profondo (Dream Cycle).</div>'

    html += """
            </div>
        </div>

        <!-- SIDEBAR: THE TECHNICAL MENTOR -->
        <div class="mentor-area">
            <div class="card">
                <div class="section-title">GUIDA AI CONCETTI TECNICI</div>
                <div class="mentor-box">
                    <b> RSI (Pressione Monetaria)</b>
                    Ti dice se tutti stanno vendendo (RSI basso) o comprando (RSI alto). L'AI compra i "saldi" quando l'RSI scende sotto 30.
                </div>
                <div class="mentor-box" style="border-left-color: #ff00ff;">
                    <b> ATR (Vento di Mercato)</b>
                    Misura quanto il prezzo  instabile. Pi  alto (tempesta), pi l'AI allarga le maglie della griglia per sicurezza.
                </div>
                <div class="mentor-box" style="border-left-color: #00ff88;">
                    <b> TREND (Bussola)</b>
                    Indica se l'asset sta crescendo o morendo nel lungo termine. L'AI lo ignora nelle griglie ma lo usa per la whitelist.
                </div>
                <div class="mentor-box" style="border-left-color: #ffcc00;">
                    <b> PnL (Tuo Profitto)</b>
                     il guadagno netto sui tuoi 50. Viene aggiornato ogni volta che il bot completa una "rivendita" in profitto.
                </div>
            </div>

            <div class="card" style="margin-top: 20px; border-color: #111;">
                <div class="section-title">DIARIO OPERATIVO LIVE</div>
                <div style="font-family: 'Space Mono'; font-size: 0.65em; color: var(--primary); max-height: 350px; overflow-y: auto;">
"""
    if activity_log:
        for line in reversed(activity_log[:40]):
            html += f'<div>> {line}</div>'
    
    html += """
                </div>
            </div>
        </div>
    </div>

    <script>
        function showView(view) {{
            document.getElementById('view-main').classList.toggle('hide', view !== 'main');
            document.getElementById('view-hunter').classList.toggle('hide', view !== 'hunter');
            document.getElementById('view-lessons').classList.toggle('hide', view !== 'lessons');
            
            document.getElementById('btn-main').classList.toggle('active', view === 'main');
            document.getElementById('btn-hunter').classList.toggle('active', view === 'hunter');
            document.getElementById('btn-lessons').classList.toggle('active', view === 'lessons');
        }}
        function updateClock() {
            // Placeholder per update dinamico se necessario
        }
        setTimeout(() => { window.location.reload(); }, 20000);
    </script>
</body>
</html>
"""
    output_path.write_text(html, encoding="utf-8")
