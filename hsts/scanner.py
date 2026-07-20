import yfinance as yf
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("hsts.scanner")

class TechnicalScanner:
    def __init__(self, ema_fast=9, ema_slow=21, ema_trend=50, ema_baseline=200):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.ema_trend = ema_trend
        self.ema_baseline = ema_baseline

    def get_technical_data(self, symbol):
        """
        Fetch historical daily price data and calculate indicators.
        """
        ticker_symbol = f"{symbol}.NS"
        try:
            ticker = yf.Ticker(ticker_symbol)
            df = ticker.history(period="6mo")
            if df.empty:
                return None
            df = df.dropna(subset=["Close"])
            if len(df) < 50:
                return None

            # 1. Moving Averages
            df["EMA_9"] = df["Close"].ewm(span=self.ema_fast, adjust=False).mean()
            df["EMA_21"] = df["Close"].ewm(span=self.ema_slow, adjust=False).mean()
            df["EMA_50"] = df["Close"].ewm(span=self.ema_trend, adjust=False).mean()
            df["EMA_200"] = df["Close"].ewm(span=self.ema_baseline, adjust=False).mean()

            # 2. RSI (Relative Strength Index)
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / (loss + 1e-9)
            df["RSI"] = 100 - (100 / (1 + rs))

            # 3. ATR (Average True Range)
            high_low = df["High"] - df["Low"]
            high_close = np.abs(df["High"] - df["Close"].shift())
            low_close = np.abs(df["Low"] - df["Close"].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            df["ATR"] = true_range.rolling(14).mean()

            # 4. Volume SMA
            df["Volume_SMA"] = df["Volume"].rolling(window=20).mean()

            return df
        except Exception as e:
            logger.error(f"Error calculating technicals for {symbol}: {e}")
            return None

    def analyze_stock(self, symbol):
        """
        Analyze a stock for swing entries.
        Outputs signal: BUY, WAIT, or SELL, along with key stats.
        """
        df = self.get_technical_data(symbol)
        if df is None:
            return {"signal": "WAIT", "reason": "No historical price data available"}

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close = latest["Close"]
        rsi = latest["RSI"]
        atr = latest["ATR"]
        volume = latest["Volume"]
        vol_sma = latest["Volume_SMA"]
        ema_9 = latest["EMA_9"]
        ema_21 = latest["EMA_21"]
        ema_50 = latest["EMA_50"]
        ema_200 = latest["EMA_200"]

        # Consensus Scoring (out of 100)
        buy_signals = 0
        total_signals = 5

        # Check conditions
        # 1. Price above medium and long term trend lines
        cond_trend = close > ema_50 and ema_50 > ema_200
        if cond_trend:
            buy_signals += 1

        # 2. Short-term bullish crossover (9 EMA > 21 EMA)
        cond_cross = ema_9 > ema_21
        if cond_cross:
            buy_signals += 1

        # 3. Momentum RSI in active zone (not overbought > 70)
        cond_rsi = 50 <= rsi <= 70
        if cond_rsi:
            buy_signals += 1

        # 4. Volume confirmation (latest volume > volume SMA)
        cond_volume = volume > vol_sma
        if cond_volume:
            buy_signals += 1

        # 5. Price close is near daily high (strong close)
        daily_range = latest["High"] - latest["Low"]
        pct_close = (close - latest["Low"]) / (daily_range + 1e-9)
        cond_strong_close = pct_close > 0.6
        if cond_strong_close:
            buy_signals += 1

        score = (buy_signals / total_signals) * 100

        # Output Signal
        if score >= 80:
            signal = "BUY"
            reason = "Strong trend structure, breakout volume, and positive RSI momentum."
        elif close < ema_21:
            signal = "SELL"
            reason = "Price closed below short-term 21 EMA support."
        else:
            signal = "WAIT"
            reason = f"Mixed indicators. Score: {score:.0f}/100"

        # Suggested Risk Levels
        stop_loss = close - (2 * atr)  # 2x ATR stop loss
        target = close + (4 * atr)     # 1:2 Risk-to-Reward ratio

        analysis = {
            "symbol": symbol,
            "close": close,
            "rsi": rsi,
            "atr": atr,
            "volume_ratio": volume / (vol_sma + 1e-9),
            "ema_50": ema_50,
            "ema_200": ema_200,
            "signal": signal,
            "reason": reason,
            "score": score,
            "suggested_sl": stop_loss,
            "suggested_target": target
        }

        return analysis
