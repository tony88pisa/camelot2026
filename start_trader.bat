@echo off
TITLE AI TRADER - Mission Control (Gemma 4 Edition)
COLOR 0B

echo ============================================================
echo   🤖 AI TRADER - AVVIO SISTEMA AUTONOMO
echo ============================================================
echo.

:: 1. Controllo Ollama
echo [1/3] Verifica Intelligenza Artificiale (Ollama)...
curl -s http://localhost:11434/api/tags > nul
if %errorlevel% neq 0 (
    echo [!] Ollama non e' attivo. Tento l'avvio...
    start "" "C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama app.exe"
    timeout /t 5
) else (
    echo [OK] Ollama e' in ascolto.
)

:: 2. Controllo Modello Gemma 4
echo [2/3] Verifica Modello Gemma 4 (9.6 GB)...
ollama list | findstr "gemma4" > nul
if %errorlevel% neq 0 (
    echo [!] Modello gemma4:latest non trovato in 'ollama list'.
    echo Per favore, rinomina il modello o scaricalo.
    pause
    exit
) else (
    echo [OK] Modello gemma4:latest pronto per il trading.
)

:: 3. Avvio Dashboard
echo [3/3] Preparazione Dashboard...
if exist dashboard.html (
    start "" dashboard.html
)

echo.
echo ============================================================
echo   🚀 BOT IN PARTENZA (Modalita' TESTNET)
echo ============================================================
echo.

:: 4. Esecuzione Bot
C:\Users\tony1\AppData\Local\Programs\Python\Python311\python.exe main.py --mode testnet

echo.
echo [!] Bot fermato. Premi un tasto per uscire.
pause > nul
