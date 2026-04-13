# scripts/check_mcp_conn.py
import sys
import os
import json

# Aggiungi src al path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from ai_trader.mcp.mcp_sse_handler import McpSseHandler

def test():
    token = 'sm_zBpkyJe6R37KT12UQaihvY_piqwTs8uDypF8B3XFu8Z5H4L2d0XWO4hX7N7d6JfYpXyb15uMXBmps5gT0ZBvaju'
    handler = McpSseHandler('https://mcp.supermemory.ai/mcp', token)

    print('--- Test Connessione SuperMemory (HTTP/Stateless) --- ')
    if handler.connect():
        print('[RUN] Recupero lista tools...')
        res = handler.list_tools()
        if res.get('ok'):
            tools = res.get('tools', [])
            print(f'[SUCCESS] Connesso! Tools trovati: {len(tools)}')
            for t in tools:
                print(f"  - {t['name']}: {t['description'][:60]}...")
        else:
            print(f"[ERROR] Errore tool: {res.get('error')}")
    else:
        print('[FAIL] Impossibile stabilire sessione (handshake fallito).')

if __name__ == "__main__":
    test()
