import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger("hsts.regime")

class MarketRegimeEngine:
    def __init__(self, index_symbol="^NSEI"):
        """
        By default, we use Nifty 50 (^NSEI) to evaluate the Indian market regime.
        """
        self.index_symbol = index_symbol

    def get_market_regime(self):
        """
        Classifies market regime as BULLISH, NEUTRAL, or BEARISH.
        Uses Nifty 50 price relation to 50 EMA and 200 EMA.
        """
        logger.info(f"Evaluating market regime using index {self.index_symbol}...")
        try:
            ticker = yf.Ticker(self.index_symbol)
            # Fetch 1 year of daily historical data
            df = ticker.history(period="1y")
            if df.empty or len(df) < 200:
                logger.warning("Insufficient history for regime calculation. Defaulting to NEUTRAL.")
                return "NEUTRAL", {}

            # Calculate EMAs
            df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
            df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

            latest_close = df["Close"].iloc[-1]
            ema_50 = df["EMA_50"].iloc[-1]
            ema_200 = df["EMA_200"].iloc[-1]

            metrics = {
                "latest_close": latest_close,
                "ema_50": ema_50,
                "ema_200": ema_200
            }

            # Regime Logic
            if latest_close > ema_50 and ema_50 > ema_200:
                regime = "BULLISH"
            elif latest_close < ema_200 and ema_50 < ema_200:
                regime = "BEARISH"
            else:
                regime = "NEUTRAL"

            logger.info(f"Market regime identified as {regime} (Close: {latest_close:.2f}, 50 EMA: {ema_50:.2f}, 200 EMA: {ema_200:.2f})")
            return regime, metrics

        except Exception as e:
            logger.error(f"Error calculating market regime: {e}")
            return "NEUTRAL", {}
