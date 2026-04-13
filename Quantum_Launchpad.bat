@echo off
TITLE QUANTUM ORACLE LAUNCHPAD V5.5
COLOR 0B

echo ============================================================
echo      QUANTUM ORACLE STATION - INITIALIZING COMMANDS
echo ============================================================
echo.

:: 1. Pulizia processi esistenti
echo [1/4] RESETTING NEURAL PIPELINES...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: 2. Avvio Bot (Main Loop) in background
echo [2/4] IGNITING ORACLE ENGINE (MAIN LOOP)...
start /min "" "C:\Users\tony1\AppData\Local\Programs\Python\Python311\python.exe" main.py --mode dry_run

:: 3. Avvio Dashboard (Browser)
echo [3/4] OPENING GLOBAL COMMAND CENTER (DASHBOARD)...
start "" "reports/index.html"

:: 4. Avvio Monitor (Terminale dedicato)
echo [4/4] DEPLOYING QUANTUM MONITOR V5.5...
timeout /t 3 /nobreak >nul
start powershell -NoExit -Command "TITLE QUANTUM_MONITOR; python monitor.py"

echo.
echo ============================================================
echo      SUCCESS: QUANTUM STATION IS NOW FULLY AUTONOMOUS
echo ============================================================
echo.
echo Puoi chiudere questa finestra. Il bot corre in background,
echo il monitor e la dashboard sono aperti per la sorveglianza.
echo.
pause
