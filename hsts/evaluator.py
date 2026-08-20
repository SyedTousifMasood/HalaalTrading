import logging
import datetime
import pandas as pd
import yfinance as yf
from hsts.journal import TradingJournal
from hsts.scanner import TechnicalScanner

logger = logging.getLogger("hsts.evaluator")

class OpenPositionEvaluator:
    def __init__(self):
        self.journal = TradingJournal()
        self.scanner = TechnicalScanner()

    def get_nifty_regime(self):
        """Fetch ^NSEI (Nifty 50) and return regime: BULLISH, BEARISH, SIDEWAYS."""
        try:
            nifty = yf.download("^NSEI", period="10d", progress=False)
            if nifty.empty:
                return "SIDEWAYS"
            close_prices = nifty["Close"].values.flatten()
            if len(close_prices) < 2:
                return "SIDEWAYS"
            
            # Simple regime check based on last 5 days
            recent_trend = (close_prices[-1] - close_prices[-5]) / close_prices[-5] * 100
            
            if recent_trend > 0.5:
                return "BULLISH"
            elif recent_trend < -0.5:
                return "BEARISH"
            else:
                return "SIDEWAYS"
        except Exception as e:
            logger.error(f"Failed to fetch Nifty regime: {e}")
            return "SIDEWAYS"

    def evaluate_5_day_rule(self):
        """
        Scans all OPEN positions in the Trading Journal.
        If a position has been held for >= 3 days, it fetches technical data
        and generates a recommendation.
        DOES NOT place orders. Read-only output.
        """
        logger.info("Evaluating OPEN positions for the 5-Day Rule (Threshold: >= 3 days)...")
        
        try:
            df = pd.read_excel(self.journal.file_path, sheet_name="Ledger")
        except Exception as e:
            logger.error(f"Failed to read Ledger: {e}")
            return []

        open_trades = df[df["Status"] == "OPEN"].copy()
        
        if open_trades.empty:
            logger.info("No open trades found.")
            return []

        today = datetime.datetime.now()
        evaluations = []

        for index, row in open_trades.iterrows():
            symbol = str(row["Symbol"]).strip()
            entry_date = row["Entry Date"]
            
            # Skip if entry_date is not valid
            if pd.isna(entry_date):
                continue
                
            if isinstance(entry_date, str):
                try:
                    entry_date = datetime.datetime.strptime(entry_date, "%Y-%m-%d")
                except:
                    continue
            elif not isinstance(entry_date, datetime.datetime):
                continue

            # Calculate days held
            days_held = (today - entry_date).days
            
            if days_held >= 3:
                # Need evaluation
                buy_price = pd.to_numeric(row["Buy Price"], errors='coerce')
                stop_loss = pd.to_numeric(row["Stop Loss"], errors='coerce')
                target = pd.to_numeric(row["Target Price"], errors='coerce')
                
                # Fetch live data
                logger.info(f"Evaluating {symbol} (held for {days_held} days)...")
                try:
                    tech_data = self.scanner.get_technical_data(symbol)
                except Exception as e:
                    logger.warning(f"Could not fetch technical data for {symbol}: {e}")
                    continue
                
                if tech_data is None or tech_data.empty:
                    continue
                
                latest = tech_data.iloc[-1]
                current_price = latest["Close"]
                rsi = latest["RSI"]
                ema20 = latest["EMA_21"]
                
                # Calculate return
                current_return = ((current_price - buy_price) / buy_price) * 100
                
                # Determine Recommendation based on momentum
                recommendation = "HOLD"
                reason = "Trend remains intact."
                
                # Rule 1: Loss of Momentum (RSI dropping below 45 or price below 20 EMA)
                if current_price < ema20:
                    recommendation = "EXIT MANUALLY"
                    reason = "Price fell below 20 EMA. Momentum lost."
                elif rsi < 45:
                    recommendation = "EXIT MANUALLY"
                    reason = "RSI dropped below 45. Weakness detected."
                
                # Rule 2: Approaching Target but stalling
                elif not pd.isna(target) and current_price >= (buy_price + (target - buy_price) * 0.8):
                    recommendation = "TRAIL STOP LOSS"
                    reason = "Close to target. Trail SL to lock in profits."
                    
                # Rule 3: Very stagnant
                elif current_return > -1.0 and current_return < 1.0 and days_held > 10:
                    recommendation = "EXIT MANUALLY"
                    reason = "Dead money. Tied up capital for > 10 days with no movement."

                evaluations.append({
                    "Symbol": symbol,
                    "Days Held": days_held,
                    "Current Return": f"{current_return:.2f}%",
                    "RSI": f"{rsi:.1f}",
                    "Status vs 20EMA": "Below" if current_price < ema20 else "Above",
                    "Recommendation": recommendation,
                    "Reason": reason
                })

        return evaluations

    def evaluate_btst_invalidation(self):
        """
        Scans all OPEN positions held for 0 or 1 days (BTST candidates).
        Checks Nifty regime, Daily chart, and 15-min chart for invalidation.
        Returns a list of symbols that should be exited tomorrow morning.
        """
        logger.info("Evaluating BTST (Day 0/1) for Premise Invalidation...")
        
        try:
            df = pd.read_excel(self.journal.file_path, sheet_name="Ledger")
        except Exception as e:
            logger.error(f"Failed to read Ledger: {e}")
            return []

        open_trades = df[df["Status"] == "OPEN"].copy()
        if open_trades.empty:
            return []

        today = datetime.datetime.now()
        invalidated_symbols = []
        
        # 1. Fetch Nifty Regime
        nifty_regime = self.get_nifty_regime()
        logger.info(f"Current Nifty 50 Regime: {nifty_regime}")

        for index, row in open_trades.iterrows():
            symbol = str(row["Symbol"]).strip()
            entry_date = row["Entry Date"]
            
            if pd.isna(entry_date):
                continue
                
            if isinstance(entry_date, str):
                try:
                    entry_date = datetime.datetime.strptime(entry_date, "%Y-%m-%d")
                except:
                    continue
            elif not isinstance(entry_date, datetime.datetime):
                continue

            days_held = (today - entry_date).days
            
            # Only evaluate new trades (0 or 1 days old)
            if days_held <= 1:
                logger.info(f"Evaluating {symbol} for BTST Invalidation...")
                try:
                    # 2. Daily check
                    tech_data = self.scanner.get_technical_data(symbol)
                    if tech_data is None or tech_data.empty:
                        continue
                        
                    daily_latest = tech_data.iloc[-1]
                    daily_close = daily_latest["Close"]
                    daily_open = daily_latest.get("Open", daily_close)
                    ema20 = daily_latest["EMA_21"]
                    
                    is_daily_weak = False
                    reason = ""
                    if daily_close < ema20:
                        is_daily_weak = True
                        reason = "Closed below 20 EMA."
                    elif daily_close < daily_open and (daily_open - daily_close) / daily_open > 0.02:
                        is_daily_weak = True
                        reason = "Bearish Engulfing / Large red daily candle."

                    if not is_daily_weak:
                        continue # Setup is fine daily
                        
                    # 3. 15-min check
                    ticker = yf.Ticker(f"{symbol}.NS")
                    df_15m = ticker.history(interval="15m", period="3d")
                    if df_15m.empty:
                        # Fallback to just daily if 15m unavailable
                        if nifty_regime == "BEARISH":
                            invalidated_symbols.append({"symbol": symbol, "reason": f"Daily weak ({reason}) + Bearish Market"})
                        continue
                        
                    closes_15m = df_15m["Close"].values
                    # Check if the last few 15m candles are making lower lows (support broken)
                    recent_support_broken = closes_15m[-1] < min(closes_15m[-10:-1])
                    
                    if nifty_regime == "BEARISH":
                        # Aggressive cut
                        invalidated_symbols.append({"symbol": symbol, "reason": f"Aggressive Cut: Daily weak ({reason}) + Bearish Market"})
                    elif nifty_regime in ["BULLISH", "SIDEWAYS"]:
                        # Need confirmation from 15m chart
                        if recent_support_broken:
                            invalidated_symbols.append({"symbol": symbol, "reason": f"Confirmed Cut: Daily weak ({reason}) AND 15m intraday support broken."})
                        else:
                            logger.info(f"{symbol} is weak on daily, but 15m support held. Holding trade.")

                except Exception as e:
                    logger.error(f"Error evaluating BTST for {symbol}: {e}")
                    continue

        return invalidated_symbols
