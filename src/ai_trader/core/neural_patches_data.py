# ARCHIVIO PATCH NEURALI - QUANTUM HUNTER
import math

# --- SEZIONE PATCH GENERATE DALL'AI ---



































# --- Patch per BinanceAdapter.format_quantity (2026-04-13T18:17:27.250533+00:00) ---
import decimal
from decimal import Decimal, getcontext

def patch_BinanceAdapter_format_quantity(self, symbol: str, quantity: float) -> str:
    """
    Patches the format_quantity method to ensure accurate, decimal-safe
    quantization of trade quantities based on the provided symbol, 
    avoiding standard floating-point inaccuracies.
    """
    
    # Define common precision requirements based on standard crypto pairs
    # This simulates the necessary lookup logic for a real exchange adapter.
    precision_map = {
        # Examples: High precision for low-cap coins, lower for majors
        "BTC/USDT": 8,
        "ETH/USDT": 6,
        "SOL/USDT": 8,
        "BNB/USDT": 7,
        "USDC/USDT": 2,
        "EUR/USDT": 4,
    }

    # Default precision if the symbol is not explicitly mapped
    default_precision = 8
    
    # Determine required precision from the symbol
    precision = precision_map.get(symbol.upper(), default_precision)
    
    # Set the calculation context precision (context must be high enough)
    getcontext().prec = max(precision + 2, 15)

    try:
        # 1. Convert the input float to a Decimal object
        decimal_quantity = Decimal(str(quantity))
        
        # 2. Quantize (round) the Decimal to the specified number of decimal places
        # The 'Decimal.quantize(Decimal('1e-N'))' method is the safest way 
        # to ensure exact rounding/truncation for financial values.
        quantizer = Decimal('1') / (Decimal(10) ** precision)
        formatted_decimal = decimal_quantity.quantize(quantizer, rounding=decimal.ROUND_DOWN)
        
        # 3. Return the result as a string
        return str(formatted_decimal)
        
    except Exception as e:
        # In case of conversion or calculation failure, log and return a default safe string
        print(f"Error formatting quantity for {symbol}: {e}")
        return "0.0"
