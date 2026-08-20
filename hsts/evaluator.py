import logging
import datetime
import pandas as pd
from hsts.journal import TradingJournal
from hsts.scanner import TechnicalScanner

logger = logging.getLogger("hsts.evaluator")

class OpenPositionEvaluator:
    def __init__(self):
        self.journal = TradingJournal()
        self.scanner = TechnicalScanner()

    def evaluate_5_day_rule(self):
        """
        Scans all OPEN positions in the Trading Journal.
        If a position has been held for >= 5 days, it fetches technical data
        and generates a recommendation.
        DOES NOT place orders. Read-only output.
        """
        logger.info("Evaluating OPEN positions for the 5-Day Rule...")
        
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
            
            if days_held >= 5:
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
