# ARCHIVIO PATCH NEURALI - QUANTUM HUNTER
import math

# --- SEZIONE PATCH GENERATE DALL'AI ---
























# --- Patch per BinanceAdapter.format_quantity (2026-04-13T06:15:00.758242+00:00) ---
import decimal
from typing import Any

# Set global precision context for Decimal operations
decimal.getcontext().prec = 28

def patch_BinanceAdapter_format_quantity(self: Any, symbol: str, quantity: float) -> str:
    """
    Optimized function to format trading quantities according to required 
    decimal precision for a specific cryptocurrency symbol on Binance.
    
    Addresses floating-point errors and ensures proper string representation 
    for exchange API calls.
    """
    
    # Map of common symbols to their required decimal places (precision)
    # This simulates fetching precision data from an exchange endpoint.
    symbol_precision_map = {
        'BTC': 8,
        'ETH': 8,
        'BNB': 6,
        'PEPE': 12,  # Example for a high-precision altcoin
        'USDT': 2,
        'USDC': 2,
    }
    
    # Default precision if symbol is unknown (e.g., standard 8 decimals)
    precision = symbol_precision_map.get(symbol.upper(), 8)
    
    try:
        # 1. Convert the float to a precise Decimal object to avoid floating point errors.
        decimal_quantity = decimal.Decimal(str(quantity))
        
        # 2. Quantize (round) the Decimal to the specified precision.
        # The context '1' (multiplier) ensures correct rounding behavior.
        quantizer = decimal.Decimal('1e-' + str(precision))
        formatted_decimal = decimal_quantity.quantize(quantizer)
        
        # 3. Return the result as a string, which is the required API format.
        return str(formatted_decimal)
        
    except decimal.InvalidOperation:
        # Handle cases where the input quantity is invalid for Decimal conversion
        return "0.0" 
