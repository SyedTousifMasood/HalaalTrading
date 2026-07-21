import yfinance as yf
import pandas as pd
import numpy as np
import logging
import math

logger = logging.getLogger("hsts.scanner")

class TechnicalScanner:
    def __init__(self, config_path="config/ai_weights.json"):
        self.config_path = config_path
        self.weights = {
            "trend": 0.25,
            "momentum": 0.25,
            "volatility": 0.15,
            "volume": 0.15,
            "levels": 0.20
        }
        self.min_threshold = 80.0
        self._load_ai_weights()

    def _load_ai_weights(self):
        import os, json
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    cfg = json.load(f)
                    if "category_weights" in cfg:
                        self.weights = cfg["category_weights"]
                        logger.info(f"Loaded AI Adaptive Category Weights: {self.weights}")
                    if "min_composite_threshold" in cfg:
                        self.min_threshold = cfg["min_composite_threshold"]
            except Exception as e:
                logger.warning(f"Could not load AI weights file: {e}")

    def get_technical_data(self, symbol):
        """
        Fetch historical daily price data and calculate all 20+ indicators.
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

            # Calculate indicators
            df = self._add_trend_indicators(df)
            df = self._add_momentum_indicators(df)
            df = self._add_volatility_indicators(df)
            df = self._add_volume_indicators(df)
            df = self._add_levels_and_advanced(df)

            return df
        except Exception as e:
            logger.error(f"Error calculating technicals for {symbol}: {e}")
            return None

    def _add_trend_indicators(self, df):
        # 1. EMAs
        df["EMA_9"] = df["Close"].ewm(span=9, adjust=False).mean()
        df["EMA_21"] = df["Close"].ewm(span=21, adjust=False).mean()
        df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
        df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

        # 2. SMAs
        df["SMA_20"] = df["Close"].rolling(window=20).mean()
        df["SMA_50"] = df["Close"].rolling(window=50).mean()
        df["SMA_200"] = df["Close"].rolling(window=200).mean()

        # 3. ADX (Average Directional Index)
        high_diff = df["High"].diff()
        low_diff = df["Low"].diff()

        df["+DM"] = np.where((high_diff > 0) & (high_diff > -low_diff), high_diff, 0)
        df["-DM"] = np.where((low_diff < 0) & (-low_diff > high_diff), -low_diff, 0)

        # True Range
        high_low = df["High"] - df["Low"]
        high_close = np.abs(df["High"] - df["Close"].shift())
        low_close = np.abs(df["Low"] - df["Close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # Smooth TR, +DM, -DM using 14-period rolling sum (Wilder's smoothing approach)
        tr_smooth = tr.rolling(window=14).sum()
        dm_plus_smooth = df["+DM"].rolling(window=14).sum()
        dm_minus_smooth = df["-DM"].rolling(window=14).sum()

        df["+DI"] = 100 * (dm_plus_smooth / (tr_smooth + 1e-9))
        df["-DI"] = 100 * (dm_minus_smooth / (tr_smooth + 1e-9))

        dx = 100 * np.abs(df["+DI"] - df["-DI"]) / (df["+DI"] + df["-DI"] + 1e-9)
        df["ADX"] = dx.rolling(window=14).mean()

        # 4. Parabolic SAR (basic implementation)
        df["SAR"] = df["Close"].copy()
        af = 0.02
        ep = df["High"].iloc[0]
        sar = df["Low"].iloc[0]
        is_uptrend = True

        sar_values = []
        for idx in range(len(df)):
            if idx == 0:
                sar_values.append(sar)
                continue
            
            prev_sar = sar
            if is_uptrend:
                sar = prev_sar + af * (ep - prev_sar)
                # Cap SAR so it doesn't exceed the lows of the last two periods
                sar = min(sar, df["Low"].iloc[idx-1], df["Low"].iloc[max(0, idx-2)])
                if df["Low"].iloc[idx] < sar:
                    is_uptrend = False
                    sar = ep
                    ep = df["Low"].iloc[idx]
                    af = 0.02
            else:
                sar = prev_sar + af * (ep - prev_sar)
                sar = max(sar, df["High"].iloc[idx-1], df["High"].iloc[max(0, idx-2)])
                if df["High"].iloc[idx] > sar:
                    is_uptrend = True
                    sar = ep
                    ep = df["High"].iloc[idx]
                    af = 0.02

            if is_uptrend:
                if df["High"].iloc[idx] > ep:
                    ep = df["High"].iloc[idx]
                    af = min(af + 0.02, 0.20)
            else:
                if df["Low"].iloc[idx] < ep:
                    ep = df["Low"].iloc[idx]
                    af = min(af + 0.02, 0.20)

            sar_values.append(sar)

        df["SAR"] = sar_values
        return df

    def _add_momentum_indicators(self, df):
        # 1. RSI
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df["RSI"] = 100 - (100 / (1 + rs))

        # 2. MACD
        df["EMA_12"] = df["Close"].ewm(span=12, adjust=False).mean()
        df["EMA_26"] = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = df["EMA_12"] - df["EMA_26"]
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()

        # 3. Stochastic Oscillator
        low_14 = df["Low"].rolling(window=14).min()
        high_14 = df["High"].rolling(window=14).max()
        df["Stoch_K"] = 100 * ((df["Close"] - low_14) / (high_14 - low_14 + 1e-9))
        df["Stoch_D"] = df["Stoch_K"].rolling(window=3).mean()

        # 4. CCI (Commodity Channel Index)
        tp = (df["High"] + df["Low"] + df["Close"]) / 3
        tp_sma = tp.rolling(window=20).mean()
        tp_mad = tp.rolling(window=20).apply(lambda x: np.fabs(x - x.mean()).mean(), raw=True)
        df["CCI"] = (tp - tp_sma) / (0.015 * tp_mad + 1e-9)

        # 5. Williams %R
        df["Will_R"] = -100 * ((high_14 - df["Close"]) / (high_14 - low_14 + 1e-9))
        return df

    def _add_volatility_indicators(self, df):
        # 1. Bollinger Bands
        std_20 = df["Close"].rolling(window=20).std()
        df["BB_Middle"] = df["Close"].rolling(window=20).mean()
        df["BB_Upper"] = df["BB_Middle"] + (2 * std_20)
        df["BB_Lower"] = df["BB_Middle"] - (2 * std_20)

        # 2. ATR
        high_low = df["High"] - df["Low"]
        high_close = np.abs(df["High"] - df["Close"].shift())
        low_close = np.abs(df["Low"] - df["Close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(window=14).mean()

        # 3. Keltner Channel (20 EMA, 2x ATR)
        df["KC_Middle"] = df["Close"].ewm(span=20, adjust=False).mean()
        df["KC_Upper"] = df["KC_Middle"] + (2 * df["ATR"])
        df["KC_Lower"] = df["KC_Middle"] - (2 * df["ATR"])

        # 4. Supertrend (simplified)
        df["Supertrend"] = df["Close"].copy()
        df["ST_Dir"] = 1
        atr_mult = 3.0

        for i in range(1, len(df)):
            hl2 = (df["High"].iloc[i] + df["Low"].iloc[i]) / 2
            basic_upper = hl2 + atr_mult * df["ATR"].iloc[i]
            basic_lower = hl2 - atr_mult * df["ATR"].iloc[i]

            prev_close = df["Close"].iloc[i-1]
            prev_upper = basic_upper
            prev_lower = basic_lower

            # Final bands
            final_upper = basic_upper if basic_upper < prev_upper or prev_close > prev_upper else prev_upper
            final_lower = basic_lower if basic_lower > prev_lower or prev_close < prev_lower else prev_lower

            # Trend Direction
            if df["Close"].iloc[i] > final_upper:
                df.loc[df.index[i], "ST_Dir"] = 1
                df.loc[df.index[i], "Supertrend"] = final_lower
            elif df["Close"].iloc[i] < final_lower:
                df.loc[df.index[i], "ST_Dir"] = -1
                df.loc[df.index[i], "Supertrend"] = final_upper
            else:
                df.loc[df.index[i], "ST_Dir"] = df["ST_Dir"].iloc[i-1]
                df.loc[df.index[i], "Supertrend"] = final_lower if df["ST_Dir"].iloc[i] == 1 else final_upper

        return df

    def _add_volume_indicators(self, df):
        # 1. OBV (On-Balance Volume)
        df["OBV"] = 0
        obv = 0
        obv_values = []
        for idx in range(len(df)):
            if idx == 0:
                obv_values.append(0)
                continue
            if df["Close"].iloc[idx] > df["Close"].iloc[idx-1]:
                obv += df["Volume"].iloc[idx]
            elif df["Close"].iloc[idx] < df["Close"].iloc[idx-1]:
                obv -= df["Volume"].iloc[idx]
            obv_values.append(obv)
        df["OBV"] = obv_values

        # 2. VWAP (Rolling 20-period volume weighted average)
        pv = (df["Close"] + df["High"] + df["Low"]) / 3 * df["Volume"]
        df["VWAP"] = pv.rolling(window=20).sum() / (df["Volume"].rolling(window=20).sum() + 1e-9)

        # 3. Volume SMA
        df["Volume_SMA"] = df["Volume"].rolling(window=20).mean()
        return df

    def _add_levels_and_advanced(self, df):
        # 1. Pivot Points (from previous day parameters)
        df["Pivot"] = (df["High"].shift() + df["Low"].shift() + df["Close"].shift()) / 3
        df["R1"] = (2 * df["Pivot"]) - df["Low"].shift()
        df["S1"] = (2 * df["Pivot"]) - df["High"].shift()
        df["R2"] = df["Pivot"] + (df["High"].shift() - df["Low"].shift())
        df["S2"] = df["Pivot"] - (df["High"].shift() - df["Low"].shift())

        # 2. Fibonacci Levels (recent 50-day swing)
        df["Swing_High"] = df["High"].rolling(window=50).max()
        df["Swing_Low"] = df["Low"].rolling(window=50).min()
        df["Fib_50"] = df["Swing_Low"] + 0.5 * (df["Swing_High"] - df["Swing_Low"])
        df["Fib_618"] = df["Swing_Low"] + 0.618 * (df["Swing_High"] - df["Swing_Low"])

        # 3. Candlesticks (Basic Doji/Hammer/Engulfing signals)
        body = np.abs(df["Close"] - df["Open"])
        candle_range = df["High"] - df["Low"]
        df["Doji"] = np.where(body <= 0.1 * candle_range, 1, 0)
        
        # Hammer pattern detection
        lower_shadow = np.minimum(df["Open"], df["Close"]) - df["Low"]
        upper_shadow = df["High"] - np.maximum(df["Open"], df["Close"])
        df["Hammer"] = np.where((lower_shadow >= 2 * body) & (upper_shadow <= 0.2 * candle_range) & (body > 0), 1, 0)

        # 4. Smart Money Concepts (Order Block Zone)
        # Placeholder for OB: We tag regions where a large volume up-candle clears preceding lows
        df["SMC_OB"] = np.where((df["Close"] > df["Open"]) & (df["Volume"] > df["Volume_SMA"] * 1.5), df["Low"], np.nan)
        df["SMC_OB"] = df["SMC_OB"].ffill()

        return df

    def analyze_stock(self, symbol):
        """
        Analyze a stock and compile category technical scores to return signal & score.
        """
        df = self.get_technical_data(symbol)
        if df is None:
            return {"signal": "WAIT", "reason": "No historical price data available"}

        latest = df.iloc[-1]
        close = latest["Close"]
        atr = latest["ATR"]

        # Category 1: Trend Signals (25% Weight)
        trend_score = 0
        if close > latest["EMA_200"]: trend_score += 25
        if close > latest["EMA_50"]: trend_score += 25
        if latest["EMA_9"] > latest["EMA_21"]: trend_score += 25
        if latest["ADX"] > 25 and latest["+DI"] > latest["-DI"]: trend_score += 25
        
        # Category 2: Momentum Signals (25% Weight)
        momentum_score = 0
        if 50 <= latest["RSI"] <= 70: momentum_score += 30
        if latest["MACD"] > latest["MACD_Signal"]: momentum_score += 30
        if latest["Stoch_K"] > latest["Stoch_D"]: momentum_score += 20
        if latest["CCI"] > 0: momentum_score += 20

        # Category 3: Volatility Signals (15% Weight)
        volatility_score = 0
        if close > latest["BB_Middle"]: volatility_score += 40
        if latest["ST_Dir"] == 1: volatility_score += 40
        if close > latest["KC_Middle"]: volatility_score += 20

        # Category 4: Volume Signals (15% Weight)
        volume_score = 0
        if latest["Volume"] > latest["Volume_SMA"]: volume_score += 50
        if close > latest["VWAP"]: volume_score += 50

        # Category 5: Levels & Advanced (20% Weight)
        levels_score = 0
        if close > latest["Pivot"]: levels_score += 40
        if close > latest["Fib_50"]: levels_score += 40
        if latest["Hammer"] == 1 or latest["Doji"] == 1: levels_score += 20

        # Composite Score (out of 100) using AI Adaptive Weights
        w_trend = self.weights.get("trend", 0.25)
        w_mom = self.weights.get("momentum", 0.25)
        w_vol = self.weights.get("volatility", 0.15)
        w_vlm = self.weights.get("volume", 0.15)
        w_lvl = self.weights.get("levels", 0.20)

        composite_score = (
            (trend_score * w_trend) + 
            (momentum_score * w_mom) + 
            (volatility_score * w_vol) + 
            (volume_score * w_vlm) + 
            (levels_score * w_lvl)
        )

        # Output Signal
        if composite_score >= self.min_threshold:
            signal = "BUY"
            reason = f"AI-optimized indicator alignment (Score: {composite_score:.0f}/100)."
        elif close < latest["EMA_21"]:
            signal = "SELL"
            reason = "Price closed below short-term 21 EMA support."
        else:
            signal = "WAIT"
            reason = f"Mixed indicators. Composite Score: {composite_score:.0f}/100"

        # Suggested Risk Levels
        stop_loss = close - (2 * atr)  # 2x ATR stop loss
        target = close + (4 * atr)     # 1:2 Risk-to-Reward ratio

        analysis = {
            "symbol": symbol,
            "close": close,
            "rsi": latest["RSI"],
            "atr": atr,
            "score": composite_score,
            "signal": signal,
            "reason": reason,
            "suggested_sl": stop_loss,
            "suggested_target": target
        }

        return analysis
