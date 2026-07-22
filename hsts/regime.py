import yfinance as yf
import pandas as pd
import logging
import os

logger = logging.getLogger("hsts.regime")

class MarketRegimeEngine:
    def __init__(self, index_symbol="^NSEI"):
        """
        By default, we use Nifty 50 (^NSEI) to evaluate the Indian market regime.
        """
        self.index_symbol = index_symbol

    def get_market_regime(self, universe_path="data/universe.csv"):
        """
        Classifies market regime into 4 states using Nifty 50 and Nifty 500 breadth:
        - STATE 1: Macro Bullish (Nifty > 200 EMA) -> Full Sizing (20%)
        - STATE 2: Bear Relief Rally (Nifty < 200 EMA, Nifty > 20 EMA, Breadth > 40%) -> Tactical Sizing (10%)
        - STATE 3: Capitulation Bottom (Nifty < 200 EMA, RSI <= 35) -> Tactical Sizing (10%)
        - STATE 4: Cash Only (Rest of bear market conditions) -> Hold Cash (0%)
        """
        logger.info(f"Evaluating market regime using index {self.index_symbol} and universe {universe_path}...")
        try:
            ticker = yf.Ticker(self.index_symbol)
            df = ticker.history(period="1y")
            if df.empty or len(df) < 200:
                logger.warning("Insufficient history for regime calculation. Defaulting to STATE 4.")
                return "STATE 4: Cash Only", {"allocation_cap": 0.0}

            # Calculate Nifty EMAs
            df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
            df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

            # Calculate Nifty RSI(14)
            delta = df["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df["RSI_14"] = 100 - (100 / (1 + rs))

            latest_close = df["Close"].iloc[-1]
            ema_20 = df["EMA_20"].iloc[-1]
            ema_200 = df["EMA_200"].iloc[-1]
            rsi_14 = df["RSI_14"].iloc[-1]

            # Calculate Breadth on top 50 universe stocks
            breadth = 0.50 # Default fallback if error
            if os.path.exists(universe_path):
                try:
                    df_uni = pd.read_csv(universe_path)
                    top_symbols = df_uni["symbol"].head(50).tolist()
                    
                    above_count = 0
                    valid_count = 0
                    
                    # Fetch history in batch
                    tickers_str = " ".join([f"{s}.NS" for s in top_symbols])
                    df_batch = yf.download(tickers_str, period="30d", group_by="ticker", progress=False)
                    
                    for sym in top_symbols:
                        ticker_key = f"{sym}.NS"
                        if ticker_key in df_batch.columns.levels[0] if isinstance(df_batch.columns, pd.MultiIndex) else ticker_key in df_batch.columns:
                            try:
                                if isinstance(df_batch.columns, pd.MultiIndex):
                                    hist = df_batch[ticker_key].dropna(subset=["Close"])
                                else:
                                    hist = df_batch.dropna(subset=["Close"])
                                if not hist.empty:
                                    c_val = hist["Close"].iloc[-1]
                                    ema_20_val = hist["Close"].ewm(span=20, adjust=False).mean().iloc[-1]
                                    if c_val > ema_20_val:
                                        above_count += 1
                                    valid_count += 1
                            except Exception:
                                pass
                    if valid_count > 0:
                        breadth = above_count / valid_count
                except Exception as b_err:
                    logger.error(f"Error calculating breadth: {b_err}")

            # State Logic
            is_macro_bullish = latest_close > ema_200
            is_oversold_bottom = (not is_macro_bullish) and (rsi_14 <= 35)
            is_relief_rally = (not is_macro_bullish) and (latest_close > ema_20) and (breadth > 0.40)

            if is_macro_bullish:
                regime = "STATE 1: Macro Bullish"
                allocation_cap = 0.20
            elif is_relief_rally:
                regime = "STATE 2: Bear Relief Rally"
                allocation_cap = 0.10
            elif is_oversold_bottom:
                regime = "STATE 3: Capitulation Bottom"
                allocation_cap = 0.10
            else:
                regime = "STATE 4: Cash Only"
                allocation_cap = 0.00

            metrics = {
                "latest_close": latest_close,
                "ema_20": ema_20,
                "ema_200": ema_200,
                "rsi_14": rsi_14,
                "breadth": breadth,
                "allocation_cap": allocation_cap
            }

            logger.info(f"Market regime identified as {regime} (Close: {latest_close:.2f}, RSI: {rsi_14:.1f}, Breadth: {breadth:.1%})")
            return regime, metrics

        except Exception as e:
            logger.error(f"Error calculating market regime: {e}")
            return "STATE 4: Cash Only", {"allocation_cap": 0.0}
