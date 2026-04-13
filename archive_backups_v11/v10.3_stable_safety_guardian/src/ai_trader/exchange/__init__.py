# src/ai_trader/exchange/__init__.py
# 2026-04-03 01:05 - Package aggregatore per gli Exchange API Adapter
"""
Exchange Adapters package.
Contiene l'interscambio con i broker (per ora Binance Testnet).
"""
from ai_trader.exchange.binance_testnet_adapter import BinanceTestnetAdapter

__all__ = ["BinanceTestnetAdapter"]
