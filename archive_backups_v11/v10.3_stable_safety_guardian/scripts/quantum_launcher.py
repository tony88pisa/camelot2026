import os
import subprocess
import time
import sys
import psutil
import requests
import json
import ast
from pathlib import Path

# Configurazione
PORT = 11434
OLLAMA_MODEL_VARIANTS = ["gemma4:latest", "gemma4-omni:latest"]
PYTHON_PATH = r"C:\Users\tony1\AppData\Local\Programs\Python\Python311\python.exe"
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def print_banner():
    banner = r"""
    ############################################################
    #                                                          #
    #      QUANTUM HUNTER V10.2 - SMART MAD ORCHESTRATOR       #
    #                                                          #
    ############################################################
    """
    print(banner)

def smart_purge():
    """
    Scansione aggressiva di sistema: chiude tutte le istanze del bot
    e resetta completamente i servizi Ollama.
    """
    print("[*] Iniziando Smart Purge del sistema...")
    my_pid = os.getpid()
    purged_count = 0
    
    # 1. Identificazione target
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            pid = proc.info['pid']
            name = proc.info['name'].lower()
            cmdline = " ".join(proc.info['cmdline'] if proc.info['cmdline'] else [])
            
            if pid == my_pid:
                continue

            # Target 1: Istanze del bot (python che esegue main.py)
            is_bot = "python" in name and "main.py" in cmdline.lower()
            
            # Target 2: Qualunque rimasuglio di Ollama (server o runner)
            is_ollama = "ollama" in name
            
            if is_bot or is_ollama:
                print(f"[!] Terminazione '{name}' (PID: {pid})...")
                proc.kill()
                purged_count += 1
                
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if purged_count > 0:
        print(f"[OK] Pulizia completata: {purged_count} processi terminati.")
        time.sleep(3) # Attesa per rilascio effettivo VRAM
    else:
        print("[OK] Sistema gi pulito. Nessun processo parassita rilevato.")

def start_ollama():
    print("[*] Avvio servizio Ollama...")
    try:
        # Avvia ollama serve in background (senza bloccare)
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[*] Attesa risposta API Ollama...")
        
        # Attendi che l'API risponda
        retries = 10
        while retries > 0:
            try:
                res = requests.get(f"http://localhost:{PORT}/api/tags", timeout=5)
                if res.status_code == 200:
                    print("[OK] Ollama API pronta.")
                    return True
            except:
                pass
            time.sleep(2)
            retries -= 1
        
        print("[ERROR] Timeout attesa Ollama API.")
        return False
    except Exception as e:
        print(f"[ERROR] Fallimento avvio Ollama: {e}")
        return False

def check_neural_integrity():
    print("[*] Audit di Integrit Neurale...")
    patch_file = PROJECT_ROOT / "src" / "ai_trader" / "core" / "neural_patches_data.py"
    
    if not patch_file.exists():
        print("[OK] Nessuna patch neurale rilevata (Factory Mode).")
        return True
        
    try:
        with open(patch_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Conta le patch (basato sugli header comment)
        patch_count = content.count("# --- Patch per")
        
        if patch_count > 0:
            print(f"[!] Rilevate {patch_count} Ottimizzazioni Neurali (Gemma 4 Mode).")
            # Verifica Sintassi
            ast.parse(content)
            print("[OK] Integrit del codice auto-generato: VALIDATA.")
        else:
            print("[OK] Registro neurale vuoto.")
        return True
    except SyntaxError as e:
        print(f"[FATAL] Corruzione nel registro neurale: {e}")
        print("[!] Consigliato: Eliminare neural_patches_data.py per ripristino di fabbrica.")
        return False
    except Exception as e:
        print(f"[ERROR] Audit neurale fallito: {e}")
        return True # Proseguiamo comunque se l'errore non  bloccante

def check_model():
    print("[*] Verifica integrit modello Gemma 4...")
    try:
        res = requests.get(f"http://localhost:{PORT}/api/tags")
        if res.status_code != 200:
            return False
        
        models = [m['name'] for m in res.json().get('models', [])]
        
        found_model = None
        for variant in OLLAMA_MODEL_VARIANTS:
            if variant in models:
                found_model = variant
                break
        
        if found_model:
            print(f"[OK] Modello '{found_model}' rilevato e pronto.")
            return True
        else:
            print(f"[WARNING] Nessun modello Gemma 4 rilevato in {models}.")
            print("[!] Tentativo di rilevamento tag parziale...")
            for m in models:
                if "gemma4" in m:
                    print(f"[OK] Rilevato modello compatibile: {m}")
                    return True
            return False
    except Exception as e:
        print(f"[ERROR] Errore durante il check del modello: {e}")
        return False

def pre_load_model():
    """Forza il caricamento del modello in VRAM prima dell'avvio del bot."""
    print("[*] Pre-caricamento modello in VRAM (Warm-up)...")
    payload = {
        "model": "gemma4:latest",
        "prompt": "Hello", 
        "stream": False
    }
    try:
        res = requests.post(f"http://localhost:{PORT}/api/generate", json=payload, timeout=60)
        if res.status_code == 200:
            print("[OK] VRAM Riscaldata e pronta.")
            return True
    except Exception as e:
        print(f"[WARNING] Warm-up fallito o timeout: {e}")
        return False

def launch_bot():
    print("\n" + "="*60)
    print("      IGNITING QUANTUM HUNTER - MAINNET MODE")
    print("="*60 + "\n")
    
    cmd = [PYTHON_PATH, "main.py", "--mode", "mainnet"]
    
    try:
        # Avvia in una NUOVA console per visibilit
        subprocess.Popen(cmd, cwd=str(PROJECT_ROOT), creationflags=subprocess.CREATE_NEW_CONSOLE)
        print("[SUCCESS] Bot avviato in una nuova finestra dedicata.")
        print("[*] Puoi chiudere questo launcher. Il sistema  ora autonomo.")
    except Exception as e:
        print(f"[FATAL] Errore durante l'avvio del bot: {e}")

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print_banner()
    
    # 1. Pulizia Totale (Smart Purge)
    smart_purge()
    
    # 2. Avvio Ollama
    if not start_ollama():
        print("[FATAL] Impossibile procedere senza Ollama.")
        input("Premi INVIO per uscire...")
        return

    # 3. Verifica Modello
    if not check_model():
        print("[FATAL] Modello Gemma 4 Mancante. Assicurati che 'gemma4:latest' sia installato.")
        input("Premi INVIO per uscire...")
        return

    # 4. Pre-caricamento (Warm-up VRAM)
    pre_load_model()

    # 5. Audit Neurale (v10.0)
    if not check_neural_integrity():
        input("Premi INVIO per uscire...")
        return

    # 5. Lancio Bot
    launch_bot()
    
    time.sleep(5)
    print("\nMission Control: Procedura terminata correttamente.")

if __name__ == "__main__":
    main()
