# src/ai_trader/analysis/market_analyzer.py
# 2026-04-12 - Analisi tecnica da candlestick Binance (RSI, EMA, ATR)
"""
MarketAnalyzer  calcola indicatori tecnici reali dai klines Binance.
Tutto in puro Python, zero dipendenze numpy/pandas.

Indicatori:
- RSI(14): Relative Strength Index  segnale overbought/oversold
- EMA(9) vs EMA(21): crossover  trend direction
- ATR(14): Average True Range  volatility measure
- Volume trend: confronto volume corrente vs media
"""

from dataclasses import dataclass
from typing import Any
from ai_trader.logging.jsonl_logger import get_logger

logger = get_logger("market_analyzer")


@dataclass
class MarketAnalysis:
    """Risultato dell'analisi tecnica per un simbolo."""
    symbol: str
    price: float
    rsi: float              # 0-100
    ema_short: float        # EMA(9)
    ema_long: float         # EMA(21)
    atr: float              # Average True Range
    trend_score: float      # -1.0 (bear) a +1.0 (bull)
    volatility_score: float # 0.0 (calmo) a 1.0 (volatile)
    regime: str             # "bull" | "bear" | "normal" | "high_chop"
    signal_quality: float   # 0.0-1.0 qualit complessiva del segnale
    volume_ratio: float     # volume corrente / media volume
    recommendation: str     # "BUY" | "SELL" | "HOLD"
    hunter_score: float     # 0.0-1.0 (potenziale gemma esplosiva)
    is_anomaly: bool        # True se rilevata anomalia significativa
    ok: bool = True
    error: str | None = None


class MarketAnalyzer:
    """
    Calcola indicatori tecnici puri da candlestick data.
    Nessuna dipendenza esterna (no numpy, no pandas, no ta-lib).
    """

    def __init__(self, exchange_adapter=None):
        self.adapter = exchange_adapter
        logger.info("MarketAnalyzer inizializzato")

    def analyze(self, symbol: str, klines: list[list] | None = None,
                interval: str = "15m", limit: int = 50) -> MarketAnalysis:
        """
        Analizza un simbolo. Se klines non  fornito, li fetcha dall'adapter.

        Args:
            symbol: Pair (es. DOGEUSDT)
            klines: Lista di candele Binance (opzionale)
            interval: Intervallo candele (default: 15m)
            limit: Numero di candele (default: 50)

        Returns:
            MarketAnalysis con tutti gli indicatori
        """
        try:
            if klines is None:
                if not self.adapter:
                    return self._error_result(symbol, "No adapter and no klines provided")
                klines = self.adapter.get_klines(symbol, interval=interval, limit=limit)
                if isinstance(klines, dict) and klines.get("_error_internal"):
                    return self._error_result(symbol, f"Klines fetch failed: {klines['_error_internal']}")

            if not klines or len(klines) < 21:
                return self._error_result(symbol, f"Not enough candles ({len(klines) if klines else 0}, need 21+)")

            # Estrai serie OHLCV
            closes = [float(k[4]) for k in klines]   # Close price
            highs = [float(k[2]) for k in klines]     # High
            lows = [float(k[3]) for k in klines]      # Low
            volumes = [float(k[5]) for k in klines]   # Volume

            price = closes[-1]

            # Calcola indicatori
            rsi = self._calc_rsi(closes, period=14)
            ema_short = self._calc_ema(closes, period=9)
            ema_long = self._calc_ema(closes, period=21)
            atr = self._calc_atr(highs, lows, closes, period=14)

            # Volume analysis
            avg_volume = sum(volumes[-14:]) / 14 if len(volumes) >= 14 else sum(volumes) / len(volumes)
            volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1.0

            # Trend score: combinazione EMA crossover + RSI
            trend_score = self._calc_trend_score(ema_short, ema_long, rsi, price)

            # Volatility score: ATR normalizzato sul prezzo
            volatility_score = (atr / price) if price > 0 else 0.0

            # Regime detection
            regime = self._detect_regime(trend_score, volatility_score, rsi)

            # Signal quality
            signal_quality = self._calc_signal_quality(rsi, trend_score, volatility_score, volume_ratio)

            # Recommendation
            recommendation = self._recommend(rsi, trend_score, volatility_score, regime)

            # --- GEM HUNTER: Anomaly Detection ---
            anomaly_data = self.detect_anomalies(closes, volumes, atr)

            result = MarketAnalysis(
                symbol=symbol,
                price=price,
                rsi=round(rsi, 2),
                ema_short=round(ema_short, 6),
                ema_long=round(ema_long, 6),
                atr=round(atr, 8),
                trend_score=round(trend_score, 3),
                volatility_score=round(volatility_score, 4),
                regime=regime,
                signal_quality=round(signal_quality, 3),
                volume_ratio=round(volume_ratio, 2),
                recommendation=recommendation,
                hunter_score=round(anomaly_data["hunter_score"], 3),
                is_anomaly=anomaly_data["is_anomaly"]
            )

            logger.info("Analisi completata",
                symbol=symbol, price=price, rsi=result.rsi,
                trend=result.trend_score, regime=regime, rec=recommendation
            )
            return result

        except Exception as e:
            logger.error("Analisi fallita", symbol=symbol, error_msg=str(e))
            return self._error_result(symbol, str(e))

    def investigate_deeply(self, symbol: str) -> dict[str, Any]:
        """
        Esegue un'indagine profonda multi-timeframe per decidere se mantenere l'asset.
        Analizza 4h (Macro), 1h (Meso) e 15m (Micro).
        
        Returns:
            dict con survival_score (0-100) e motivazione investigativa.
        """
        if not self.adapter:
            return {"survival_score": 50, "reason": "No adapter", "ok": False}
            
        logger.info("Investigazione profonda in corso...", symbol=symbol)
        
        # 1. Fetch multi-timeframe data
        intervals = ["4h", "1h", "15m"]
        scores = {}
        
        for timeframe in intervals:
            klines = self.adapter.get_klines(symbol, interval=timeframe, limit=20)
            if not klines or len(klines) < 10:
                scores[timeframe] = 50.0 # Neutral fallback
                continue
                
            closes = [float(k[4]) for k in klines]
            rsi = self._calc_rsi(closes, period=14)
            ema9 = self._calc_ema(closes, period=9)
            ema21 = self._calc_ema(closes, period=21)
            
            # Trend locale: EMA crossover (60%) + RSI (40%)
            ema_trend = 1.0 if ema9 > ema21 else -1.0
            rsi_trend = (rsi - 50) / 50
            scores[timeframe] = (ema_trend * 0.6 + rsi_trend * 0.4) * 50 + 50 # Normalize to 0-100

        # 2. Punteggio Composito Pesato (Macro pesa il 50%, Meso 30%, Micro 20%)
        survival_score = (scores["4h"] * 0.5) + (scores["1h"] * 0.3) + (scores["15m"] * 0.2)
        
        reason = "Trend Macro Solido" if scores["4h"] > 70 else "Debolezza Incombente"
        if survival_score < 40:
            reason = "Trend Compromesso su tutti i timeframe"
        elif survival_score > 60 and scores["15m"] < 30:
            reason = "Macro OK ma correzione locale in corso (HOLD)"

        return {
            "symbol": symbol,
            "survival_score": round(survival_score, 2),
            "timeframe_scores": scores,
            "reason": reason,
            "ok": True
        }

    # -------------------------------------------------------------------------
    # Indicatori tecnici puri
    # -------------------------------------------------------------------------

    @staticmethod
    def _calc_rsi(closes: list[float], period: int = 14) -> float:
        """Calcola RSI (Relative Strength Index)  Wilder's smoothing."""
        if len(closes) < period + 1:
            return 50.0  # neutral fallback

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

        # Primi 'period' delta per seed iniziale
        gains = [d if d > 0 else 0 for d in deltas[:period]]
        losses = [-d if d < 0 else 0 for d in deltas[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # Wilder's smoothing per i delta restanti
        for d in deltas[period:]:
            gain = d if d > 0 else 0
            loss = -d if d < 0 else 0
            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _calc_ema(values: list[float], period: int) -> float:
        """Calcola EMA (Exponential Moving Average)."""
        if len(values) < period:
            return values[-1] if values else 0.0

        multiplier = 2.0 / (period + 1)
        ema = sum(values[:period]) / period  # SMA come seed

        for val in values[period:]:
            ema = (val - ema) * multiplier + ema

        return ema

    @staticmethod
    def _calc_atr(highs: list[float], lows: list[float], closes: list[float],
                  period: int = 14) -> float:
        """Calcola ATR (Average True Range)  Wilder's smoothing."""
        if len(closes) < period + 1:
            return 0.0

        true_ranges = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            true_ranges.append(tr)

        if len(true_ranges) < period:
            return sum(true_ranges) / len(true_ranges)

        atr = sum(true_ranges[:period]) / period
        for tr in true_ranges[period:]:
            atr = (atr * (period - 1) + tr) / period

        return atr

    # -------------------------------------------------------------------------
    # Scoring e Regime Detection
    # -------------------------------------------------------------------------

    def _calc_trend_score(self, ema_short: float, ema_long: float,
                          rsi: float, price: float) -> float:
        """
        Trend score da -1.0 (forte bear) a +1.0 (forte bull).
        Combina EMA crossover e RSI direction.
        """
        # EMA crossover component (-0.5 to +0.5)
        if ema_long > 0:
            ema_pct = (ema_short - ema_long) / ema_long
            ema_component = max(-0.5, min(0.5, ema_pct * 10))
        else:
            ema_component = 0.0

        # RSI component (-0.5 to +0.5)
        rsi_component = (rsi - 50) / 100  # range: -0.5 to +0.5

        return max(-1.0, min(1.0, ema_component + rsi_component))

    def _detect_regime(self, trend_score: float, volatility_score: float,
                       rsi: float) -> str:
        """Classifica il regime di mercato corrente."""
        if volatility_score > 0.04:
            return "high_chop"
        if trend_score > 0.3:
            return "bull"
        if trend_score < -0.3:
            return "bear"
        return "normal"

    def _calc_signal_quality(self, rsi: float, trend_score: float,
                             volatility_score: float, volume_ratio: float) -> float:
        """
        Qualit segnale 0.0-1.0.
        Alta qualit = RSI non estremo, trend chiaro, volume decente.
        """
        # RSI contribution: penalizza estremi
        if 30 <= rsi <= 70:
            rsi_score = 0.3
        elif 20 <= rsi <= 80:
            rsi_score = 0.2
        else:
            rsi_score = 0.1

        # Trend clarity
        trend_clarity = min(0.3, abs(trend_score) * 0.4)

        # Volume confirmation
        vol_score = min(0.2, volume_ratio * 0.1) if volume_ratio > 0.5 else 0.0

        # Volatility (moderate is good for grid)
        vol_bonus = 0.2 if 0.005 < volatility_score < 0.03 else 0.1

        return min(1.0, rsi_score + trend_clarity + vol_score + vol_bonus)

    def _recommend(self, rsi: float, trend_score: float,
                   volatility_score: float, regime: str) -> str:
        """
        Genera raccomandazione BUY/SELL/HOLD per Grid Trading.
        Grid compra quando RSI basso + trend non fortemente negativo.
        Grid vende quando RSI alto + trend non fortemente positivo.
        """
        if regime == "high_chop":
            return "HOLD"

        # RSI oversold + trend non negativo  BUY
        if rsi < 35 and trend_score > -0.3:
            return "BUY"

        # RSI overbought + trend non fortemente positivo  SELL
        if rsi > 65 and trend_score < 0.5:
            return "SELL"

        # Trend favorevole con RSI medio  BUY
        if trend_score > 0.2 and rsi < 55:
            return "BUY"

        return "HOLD"

    def detect_anomalies(self, closes: list[float], volumes: list[float], atr: float) -> dict[str, Any]:
        """
        Rileva anomalie di volume e prezzo per identificare 'Gemme'.
        Hunter Score > 0.7 indica alta probabilit di movimento esplosivo.
        """
        if not closes or not volumes or len(closes) < 14:
            return {"hunter_score": 0.0, "is_anomaly": False}

        # 1. Volume Spike (Volume attuale vs Media 14 periodi)
        avg_vol = sum(volumes[-14:-1]) / 13
        vol_spike = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
        
        # 2. Price Surge (Variazione prezzo vs ATR)
        price_change = abs(closes[-1] - closes[-2])
        price_spike = price_change / atr if atr > 0 else 0.0
        
        # Calcolo Hunter Score (normale: 0.0 - 1.0)
        # Il volume pesa il 60%, il prezzo il 40%
        vol_component = min(1.0, (vol_spike / 5.0)) # Massimo score a 5x volume
        price_component = min(1.0, (price_spike / 3.0)) # Massimo score a 3x ATR
        
        hunter_score = (vol_component * 0.6) + (price_component * 0.4)
        is_anomaly = hunter_score > 0.6
        
        return {
            "hunter_score": hunter_score,
            "is_anomaly": is_anomaly,
            "vol_spike": round(vol_spike, 2),
            "price_spike": round(price_spike, 2)
        }

    def _error_result(self, symbol: str, error: str) -> MarketAnalysis:
        """Costruisce risultato di errore."""
        return MarketAnalysis(
            symbol=symbol, price=0.0, rsi=50.0, ema_short=0.0, ema_long=0.0,
            atr=0.0, trend_score=0.0, volatility_score=0.0, regime="unknown",
            signal_quality=0.0, volume_ratio=0.0, recommendation="HOLD",
            ok=False, error=error
        )
