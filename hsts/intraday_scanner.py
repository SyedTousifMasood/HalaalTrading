import yfinance as yf
import pandas as pd
import numpy as np
import logging
from hsts.sharia import ShariaScreeningEngine

logger = logging.getLogger("hsts.intraday_scanner")

class HalalIntradayScanner:
    def __init__(self, universe_csv_path="data/universe.csv"):
        self.universe_csv_path = universe_csv_path
        self.sharia_engine = ShariaScreeningEngine(universe_csv_path)

    def calculate_indicators(self, df):
        """
        Calculate intraday technical indicators: VWAP, ORB, Momentum Breakout, RSI, MACD, and ATR.
        """
        df = df.copy()
        df.index = pd.to_datetime(df.index)
        
        # 1. Typical Price & Daily VWAP
        df["Typical_Price"] = (df["High"] + df["Low"] + df["Close"]) / 3
        df["TP_Vol"] = df["Typical_Price"] * df["Volume"]
        
        # Reset VWAP daily by grouping by date
        df["Date_Group"] = df.index.date
        df["Cum_TP_Vol"] = df.groupby("Date_Group")["TP_Vol"].cumsum()
        df["Cum_Vol"] = df.groupby("Date_Group")["Volume"].cumsum()
        df["VWAP"] = df["Cum_TP_Vol"] / (df["Cum_Vol"] + 1e-9)
        
        # 2. Opening Range Breakout (ORB) - 15m high of the first candle of the day
        # Identify the first candle of each day
        df["Is_First_Candle"] = df.groupby("Date_Group").cumcount() == 0
        
        # Capture the high and low of the first candle
        first_candles = df[df["Is_First_Candle"]][["High", "Low"]].copy()
        first_candles["Date_Group"] = first_candles.index.date
        first_candles = first_candles.rename(columns={"High": "OR_High", "Low": "OR_Low"})
        
        # Merge back to map OR_High and OR_Low to all candles of that day
        df = df.merge(first_candles[["Date_Group", "OR_High", "OR_Low"]], on="Date_Group", how="left")
        df.index = pd.to_datetime(df.index)  # restore index after merge
        
        # Check if price breaks above the opening range high
        df["ORB_Signal"] = df["Close"] > df["OR_High"]
        
        # 3. Momentum Breakout (20-candle high & volume spike)
        df["High_20"] = df["High"].shift(1).rolling(window=20).max()
        df["Avg_Vol_20"] = df["Volume"].shift(1).rolling(window=20).mean()
        df["Mom_Breakout"] = (df["Close"] > df["High_20"]) & (df["Volume"] > 1.5 * df["Avg_Vol_20"])
        
        # 4. Intraday RSI (14)
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df["RSI"] = 100 - (100 / (1 + rs))
        
        # 5. MACD (12, 26, 9)
        df["EMA_12"] = df["Close"].ewm(span=12, adjust=False).mean()
        df["EMA_26"] = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = df["EMA_12"] - df["EMA_26"]
        df["MACD_Signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
        
        # 6. ATR (14)
        high_low = df["High"] - df["Low"]
        high_close = np.abs(df["High"] - df["Close"].shift())
        low_close = np.abs(df["Low"] - df["Close"].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["ATR"] = tr.rolling(window=14).mean()
        
        return df

    def scan_universe(self):
        """
        Batch scan Nifty Shariah pre-screened symbols for fast, real-time execution.
        """
        candidates = []
        all_symbols = self.sharia_engine.universe
        
        # Filter to pre-screened nifty_shariah only to prevent slow yfinance balance sheet downloads
        compliant_df = all_symbols[all_symbols["source"] == "nifty_shariah"]
        compliant_symbols = compliant_df["symbol"].tolist()
        
        # Filter out known delisted/unresponsive symbols to prevent yfinance threading deadlocks
        bad_symbols = {"LTIM", "BIRLASOFT", "OBEROIREAL", "GUJGASLTD", "JBCHEPHARM", "SPICEJET", "CSM"}
        compliant_symbols = [sym for sym in compliant_symbols if sym not in bad_symbols]
        
        logger.info(f"Filtered to {len(compliant_symbols)} pre-screened Nifty Shariah symbols. Starting batch download...")
        
        # Batch download 15m candles in chunks of 30 to prevent OpenBLAS/yfinance threading memory exhaustion
        tickers_map = {f"{sym}.NS": sym for sym in compliant_symbols}
        tickers_list = list(tickers_map.keys())
        chunk_size = 30
        chunks = [tickers_list[i:i + chunk_size] for i in range(0, len(tickers_list), chunk_size)]
        
        for idx, chunk in enumerate(chunks):
            logger.info(f"Downloading intraday batch {idx+1}/{len(chunks)}... ({len(chunk)} tickers)")
            try:
                # Use threads=True but with smaller batch size to avoid memory exhaustion
                df_batch = yf.download(chunk, interval="15m", period="5d", group_by="ticker", progress=False, threads=True, timeout=10)
                if df_batch.empty:
                    continue
                
                # Check format of returned batch columns
                has_multiindex = isinstance(df_batch.columns, pd.MultiIndex)
                
                for ns_sym in chunk:
                    sym = tickers_map[ns_sym]
                    df = None
                    if len(chunk) == 1:
                        df = df_batch.dropna(subset=["Close"])
                    elif has_multiindex and ns_sym in df_batch.columns.levels[0]:
                        df = df_batch[ns_sym].dropna(subset=["Close"])
                        
                    if df is None or df.empty or len(df) < 30:
                        continue
                        
                    try:
                        df = self.calculate_indicators(df)
                        latest = df.iloc[-1]
                        
                        # Relaxed breakout criteria: check if breakout occurred at any point today (last 25 candles)
                        # but ensure the stock ended the day bullishly (Close > VWAP, RSI > 50, MACD > Signal)
                        recent_candles = df.tail(25)
                        had_orb = recent_candles["ORB_Signal"].any()
                        had_mom = recent_candles["Mom_Breakout"].any()
                        
                        is_bullish = (
                          latest["Close"] > latest["VWAP"] and
                          had_orb and
                          had_mom and
                          latest["RSI"] > 50.0 and
                          latest["MACD"] > latest["MACD_Signal"]
                        )
                        
                        if not is_bullish:
                            continue
                            
                        # Score calculation
                        rsi_score = min(40, (latest["RSI"] - 50) * 2) if latest["RSI"] > 50 else 0
                        vwap_margin = (latest["Close"] - latest["VWAP"]) / latest["VWAP"]
                        vwap_score = min(30, vwap_margin * 1000)
                        vol_multiplier = latest["Volume"] / (latest["Avg_Vol_20"] + 1e-9)
                        vol_score = min(30, (vol_multiplier - 1.5) * 10)
                        
                        composite_score = int(50 + rsi_score + vwap_score + vol_score)
                        composite_score = max(50, min(100, composite_score))
                        
                        entry_price = float(round(latest["Close"], 2))
                        
                        # Estimate daily ATR from 15m data (5 days of history) to prevent paper-thin targets
                        df["Date_Only"] = df.index.date
                        daily_ranges = df.groupby("Date_Only").apply(lambda x: x["High"].max() - x["Low"].min(), include_groups=False)
                        est_daily_atr = float(daily_ranges.mean())
                        if pd.isna(est_daily_atr) or est_daily_atr <= 0:
                            est_daily_atr = entry_price * 0.03 # fallback to 3% daily range
                        
                        # Set Stop-Loss at 0.75x Daily ATR and Target at 1.5x Daily ATR (yielding a clean 1:2.0 risk-to-reward)
                        sl = float(round(entry_price - (0.75 * est_daily_atr), 2))
                        target = float(round(entry_price + (1.5 * est_daily_atr), 2))
                        
                        # Ensure both stop-loss and target conform to 0.05 tick size
                        sl = float(round(sl * 20) / 20)
                        target = float(round(target * 20) / 20)
                        
                        candidates.append({
                            "symbol": sym,
                            "score": composite_score,
                            "entry": entry_price,
                            "stop_loss": sl,
                            "target": target,
                            "rr_ratio": 2.0
                        })
                    except Exception as ex:
                        continue
            except Exception as e:
                logger.error(f"Error in batch intraday download/scan chunk: {e}")
            
        # Sort candidates by composite score descending
        candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
        return candidates
