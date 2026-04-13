# src/ai_trader/exchange/binance_streamer.py
# 2026-04-13 - Apex Predator v11.0: Real-time L2 Order Book Manager
"""
BinanceStreamer  Gestore WebSocket asincrono per l'integrit dei dati a millisecondi.
Mantiene un libro ordini locale sincronizzato (Snapshot + Diff stream).
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from binance import AsyncClient, BinanceSocketManager
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("binance_streamer")

class BinanceStreamer:
    """
    Gestisce connessioni WebSocket multiple per mantenere l'Order Book in tempo reale.
    Implementa la logica di sincronizzazione richiesta da Binance per i local order book.
    """

    def __init__(self, api_key: str = "", api_secret: str = ""):
        self.client: Optional[AsyncClient] = None
        self.bsm: Optional[BinanceSocketManager] = None
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Struttura: {symbol: {"bids": {price: qty}, "asks": {price: qty}, "lastUpdateId": int}}
        self.order_books: Dict[str, Dict[str, Any]] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self._syncing_symbols = set()
        self._running = False
        self._running_internal = False

    async def start(self):
        """Avvia il client asincrono con gestione retry per IP Ban."""
        while self._running_internal is False:
            try:
                self.client = await AsyncClient.create(self.api_key, self.api_secret)
                self.bsm = BinanceSocketManager(self.client)
                self._running_internal = True
                logger.info("BinanceStreamer: Nucleo Asincrono Avviato (Connessione Stabilita)")
            except Exception as e:
                logger.warning(f"BinanceStreamer: Errore connessione iniziale. Riprovo tra 15s... Error: {str(e)}")
                await asyncio.sleep(15)
        
        self._running = True

    async def stop(self):
        """Ferma tutti gli stream e chiude il client."""
        self._running = False
        for symbol, task in self.active_tasks.items():
            task.cancel()
        if self.client:
            await self.client.close_connection()
        logger.info("BinanceStreamer: Nucleo Asincrono Fermato")

    async def subscribe_depth(self, symbol: str):
        """Sottoscrive lo stream diffDepth per un simbolo e avvia la sincronizzazione."""
        if symbol in self.active_tasks:
            return

        # 1. Inizializza struttura vuota (buffer)
        self.order_books[symbol] = {"bids": {}, "asks": {}, "lastUpdateId": 0, "synchronized": False, "buffer": []}
        
        # 2. Avvia task di gestione stream
        task = asyncio.create_task(self._depth_listener(symbol))
        self.active_tasks[symbol] = task
        logger.info(f"Sottoscrizione Depth: {symbol} avviata")

    async def _depth_listener(self, symbol: str):
        """Worker asincrono per lo stream di profondit."""
        try:
            # v11.6.2: Normalizzazione case-insensitive per WebSocket Binance
            symbol_ws = symbol.lower()
            socket = self.bsm.depth_socket(symbol_ws)
            
            async with socket as stream:
                while self._running:
                    msg = await stream.recv()
                    if not msg: continue
                    
                    # Gestione sincronizzazione v11.0
                    await self._process_depth_event(symbol, msg)
                    
        except asyncio.CancelledError:
            logger.info(f"Stream depth {symbol} cancellato")
        except Exception as e:
            logger.error(f"Errore Stream depth {symbol}", error=str(e))
            # v11.0: Auto-reconnect strategico
            await asyncio.sleep(5)
            if self._running:
                await self.subscribe_depth(symbol)

    async def _process_depth_event(self, symbol: str, event: dict):
        """Processa l'evento diffDepth e lo applica al libro locale."""
        book = self.order_books[symbol]
        
        # Se non siamo ancora sincronizzati, buffera l'evento e chiedi lo snapshot
        if not book["synchronized"]:
            book["buffer"].append(event)
            # v11.6.2: Feedback visivo riempimento buffer (ogni 5 eventi)
            if len(book["buffer"]) % 5 == 0:
                logger.info(f"Vision L2 {symbol}: Caricamento buffer {len(book['buffer'])}/10...")
                
            # v11.9.5: Soglia aumentata a 50 per garantire un ponte solido
            if len(book["buffer"]) >= 50 and symbol not in self._syncing_symbols: 
                asyncio.create_task(self._sync_with_snapshot(symbol))
            return

        # Verifica integrit ID sequenza (fondamentale per perfezione 2026)
        last_id = book["lastUpdateId"]
        if event['u'] <= last_id:
            return # Salta eventi vecchi
        
        if event['U'] != last_id + 1:
            # Salto di sequenza rilevato: Risincronizzazione forzata
            logger.warning(f"Sincronizzazione persa per {symbol}. Richiedo nuovo snapshot.")
            book["synchronized"] = False
            book["buffer"] = [event]
            await self._sync_with_snapshot(symbol)
            return

        # Applica aggiornamenti
        self._apply_diff(book, event)
        book["lastUpdateId"] = event['u']

    def _apply_diff(self, book: dict, event: dict):
        """Applica puntualmente i diff bids/asks."""
        for side in ['bids', 'asks']:
            key = 'b' if side == 'bids' else 'a'
            for price, qty in event[key]:
                price_f = float(price)
                qty_f = float(qty)
                if qty_f == 0:
                    book[side].pop(price_f, None)
                else:
                    book[side][price_f] = qty_f

    async def _sync_with_snapshot(self, symbol: str):
        """Sincronizza il libro corrente con uno snapshot REST."""
        if symbol in self._syncing_symbols:
            return
            
        self._syncing_symbols.add(symbol)
        try:
            # v11.9.1: Ridotto a 100 (da 5000) per garantire un rapido fetch senza Gap L2.
            logger.info(f"Richiesta Snapshot L2 Apex (100 levels) per {symbol}...")
            snapshot = await self.client.get_order_book(symbol=symbol, limit=100)
            last_id = snapshot['lastUpdateId']
            
            book = self.order_books[symbol]
            book["bids"] = {float(p): float(q) for p, q in snapshot['bids']}
            book["asks"] = {float(p): float(q) for p, q in snapshot['asks']}
            book["lastUpdateId"] = last_id
            
            # Applica i buffer accumulati (v11.6 Crystal Vision)
            applied_count = 0
            for event in book["buffer"]:
                if event['U'] <= last_id + 1 <= event['u']:
                    self._apply_diff(book, event)
                    book["lastUpdateId"] = event['u']
                    book["synchronized"] = True
                    applied_count += 1
                elif applied_count > 0:
                    self._apply_diff(book, event)
                    book["lastUpdateId"] = event['u']
            
            if applied_count > 0:
                book["buffer"] = []
                logger.info(f"Sincronizzazione L2 completata per {symbol} (Apex Predator Active)")
            else:
                logger.warning(f"Gap L2 rilevato per {symbol}. Attesa buffer 5s per sovrapposizione (Stealth Gold)...")
                # v11.9.2: Cooldown radicale per proteggere l'IP da ban del peso API
                await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Errore sincronizzazione snapshot {symbol}", error=str(e))
            await asyncio.sleep(5)
        finally:
            self._syncing_symbols.remove(symbol)

    def get_order_book(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Restituisce lo stato corrente (ordinato) del libro ordini sync."""
        if symbol not in self.order_books or not self.order_books[symbol]["synchronized"]:
            return None
        
        book = self.order_books[symbol]
        # Restituiamo i top 20 livelli ordinati
        sorted_bids = sorted(book["bids"].items(), key=lambda x: x[0], reverse=True)[:20]
        sorted_asks = sorted(book["asks"].items(), key=lambda x: x[0])[:20]
        
        return {
            "symbol": symbol,
            "bids": sorted_bids,
            "asks": sorted_asks,
            "lastUpdateId": book["lastUpdateId"]
        }
