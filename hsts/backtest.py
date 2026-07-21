import yfinance as yf
import pandas as pd
import numpy as np
import logging
import datetime
from hsts.sharia import ShariaScreeningEngine
from hsts.scanner import TechnicalScanner
from hsts.risk import RiskManagementEngine

logger = logging.getLogger("hsts.backtest")

class BacktestEngine:
    def __init__(self, initial_capital=100000.0, max_risk_per_trade=0.01, max_allocation=0.20):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_risk_per_trade = max_risk_per_trade
        self.max_allocation = max_allocation
        
        self.sharia_engine = ShariaScreeningEngine()
        self.scanner = TechnicalScanner()
        self.risk_engine = RiskManagementEngine(
            max_portfolio_risk_per_trade=max_risk_per_trade,
            min_risk_reward_ratio=2.0
        )
        
        self.open_trades = []
        self.completed_trades = []
        self.equity_curve = []

    def run_backtest(self, universe_path="data/universe.csv", period="1y"):
        """
        Run a historical backtest over the specified period (e.g. '1y', '2y').
        """
        logger.info(f"Starting historical backtest for period={period} with Initial Capital = INR {self.initial_capital:,.2f}...")
        
        # 1. Download Nifty 50 Index history for Market Regime
        nifty = yf.Ticker("^NSEI").history(period=period)
        if nifty.empty:
            logger.error("Failed to fetch Nifty 50 historical data for backtesting.")
            return None
            
        nifty["EMA_50"] = nifty["Close"].ewm(span=50, adjust=False).mean()
        nifty["EMA_200"] = nifty["Close"].ewm(span=200, adjust=False).mean()
        nifty = nifty.dropna(subset=["EMA_200"])

        # 2. Download Universe Stocks history
        df_univ = pd.read_csv(universe_path)
        stock_data = {}
        
        for idx, row in df_univ.iterrows():
            sym = row["symbol"]
            # Screen Sharia compliance
            is_halal, _ = self.sharia_engine.screen_stock(sym)
            if not is_halal:
                continue
                
            ticker_sym = f"{sym}.NS"
            df = yf.Ticker(ticker_sym).history(period=period)
            if not df.empty and len(df) >= 50:
                df = df.dropna(subset=["Close"])
                df = self.scanner._add_trend_indicators(df)
                df = self.scanner._add_momentum_indicators(df)
                df = self.scanner._add_volatility_indicators(df)
                df = self.scanner._add_volume_indicators(df)
                df = self.scanner._add_levels_and_advanced(df)
                stock_data[sym] = df

        if not stock_data:
            logger.error("No compliant stock historical data available for backtest.")
            return None

        # 3. Bar-by-bar simulation loop
        common_dates = nifty.index
        
        for date in common_dates:
            nifty_row = nifty.loc[date]
            nifty_close = nifty_row["Close"]
            ema_200 = nifty_row["EMA_200"]
            
            # Determine Regime on day t
            regime = "BEARISH" if nifty_close < ema_200 else "BULLISH"

            # Step A: Manage Open Trades Exits
            still_open = []
            for trade in self.open_trades:
                sym = trade["symbol"]
                if sym in stock_data and date in stock_data[sym].index:
                    bar = stock_data[sym].loc[date]
                    low = bar["Low"]
                    high = bar["High"]
                    close = bar["Close"]
                    
                    trade["sessions_held"] += 1
                    
                    # Check Stop Loss
                    if low <= trade["stop_loss"]:
                        trade["exit_date"] = date.strftime("%Y-%m-%d")
                        trade["exit_price"] = trade["stop_loss"]
                        trade["pnl"] = (trade["stop_loss"] - trade["entry_price"]) * trade["qty"]
                        trade["status"] = "LOSS"
                        self.current_capital += (trade["qty"] * trade["stop_loss"])
                        self.completed_trades.append(trade)
                    # Check Target
                    elif high >= trade["target"]:
                        trade["exit_date"] = date.strftime("%Y-%m-%d")
                        trade["exit_price"] = trade["target"]
                        trade["pnl"] = (trade["target"] - trade["entry_price"]) * trade["qty"]
                        trade["status"] = "WIN"
                        self.current_capital += (trade["qty"] * trade["target"])
                        self.completed_trades.append(trade)
                    # Check Session Limit (7 sessions max)
                    elif trade["sessions_held"] >= 7:
                        trade["exit_date"] = date.strftime("%Y-%m-%d")
                        trade["exit_price"] = close
                        trade["pnl"] = (close - trade["entry_price"]) * trade["qty"]
                        trade["status"] = "WIN" if close >= trade["entry_price"] else "LOSS"
                        self.current_capital += (trade["qty"] * close)
                        self.completed_trades.append(trade)
                    else:
                        still_open.append(trade)
                else:
                    still_open.append(trade)
            
            self.open_trades = still_open

            # Step B: Enter New Positions (If Regime is NOT BEARISH)
            if regime != "BEARISH":
                for sym, df in stock_data.items():
                    # Skip if already holding this symbol
                    if any(t["symbol"] == sym for t in self.open_trades):
                        continue

                    if date in df.index:
                        bar = df.loc[date]
                        close = bar["Close"]
                        atr = bar["ATR"]
                        
                        if pd.isna(close) or pd.isna(atr) or atr <= 0:
                            continue

                        # Calculate Score on day t
                        trend_score = 0
                        if close > bar["EMA_200"]: trend_score += 25
                        if close > bar["EMA_50"]: trend_score += 25
                        if bar["EMA_9"] > bar["EMA_21"]: trend_score += 25
                        if bar["ADX"] > 25 and bar["+DI"] > bar["-DI"]: trend_score += 25
                        
                        momentum_score = 0
                        if 50 <= bar["RSI"] <= 70: momentum_score += 30
                        if bar["MACD"] > bar["MACD_Signal"]: momentum_score += 30
                        if bar["Stoch_K"] > bar["Stoch_D"]: momentum_score += 20
                        if bar["CCI"] > 0: momentum_score += 20

                        volatility_score = 0
                        if close > bar["BB_Middle"]: volatility_score += 40
                        if bar["ST_Dir"] == 1: volatility_score += 40
                        if close > bar["KC_Middle"]: volatility_score += 20

                        volume_score = 0
                        if bar["Volume"] > bar["Volume_SMA"]: volume_score += 50
                        if close > bar["VWAP"]: volume_score += 50

                        levels_score = 0
                        if close > bar["Pivot"]: levels_score += 40
                        if close > bar["Fib_50"]: levels_score += 40
                        if bar["Hammer"] == 1 or bar["Doji"] == 1: levels_score += 20

                        composite_score = (
                            (trend_score * 0.25) + 
                            (momentum_score * 0.25) + 
                            (volatility_score * 0.15) + 
                            (volume_score * 0.15) + 
                            (levels_score * 0.20)
                        )

                        # Trigger Signal (Score >= 80)
                        if composite_score >= 80:
                            stop_loss = close - (2 * atr)
                            target = close + (4 * atr)
                            
                            pos = self.risk_engine.calculate_position_size(
                                total_capital=self.current_capital,
                                entry_price=close,
                                stop_loss_price=stop_loss
                            )
                            
                            if pos and pos["quantity"] > 0:
                                qty = pos["quantity"]
                                cost = qty * close
                                if cost <= self.current_capital:
                                    self.current_capital -= cost
                                    self.open_trades.append({
                                        "symbol": sym,
                                        "entry_date": date.strftime("%Y-%m-%d"),
                                        "entry_price": close,
                                        "stop_loss": stop_loss,
                                        "target": target,
                                        "qty": qty,
                                        "score": composite_score,
                                        "sessions_held": 0
                                    })

            # Calculate daily equity
            open_val = sum(t["qty"] * stock_data[t["symbol"]].loc[date]["Close"] 
                           for t in self.open_trades if date in stock_data[t["symbol"]].index)
            total_equity = self.current_capital + open_val
            self.equity_curve.append({"date": date, "equity": total_equity, "nifty": nifty_close})

        return self.generate_performance_report(nifty)

    def generate_performance_report(self, nifty_df):
        """
        Compute statistics and generate a performance metrics summary.
        """
        if not self.equity_curve:
            return None

        df_eq = pd.DataFrame(self.equity_curve)
        
        # Returns
        final_equity = df_eq["equity"].iloc[-1]
        total_return_pct = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        
        nifty_start = nifty_df["Close"].iloc[0]
        nifty_end = nifty_df["Close"].iloc[-1]
        benchmark_return_pct = ((nifty_end - nifty_start) / nifty_start) * 100

        # Drawdown
        df_eq["peak"] = df_eq["equity"].cummax()
        df_eq["drawdown"] = (df_eq["equity"] - df_eq["peak"]) / df_eq["peak"]
        max_drawdown_pct = df_eq["drawdown"].min() * 100

        # Trade Stats
        total_trades = len(self.completed_trades)
        wins = [t for t in self.completed_trades if t["status"] == "WIN"]
        losses = [t for t in self.completed_trades if t["status"] == "LOSS"]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0

        gross_profit = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        # Sharpe Ratio (annualized)
        df_eq["daily_return"] = df_eq["equity"].pct_change().fillna(0)
        mean_ret = df_eq["daily_return"].mean()
        std_ret = df_eq["daily_return"].std()
        sharpe_ratio = (mean_ret / (std_ret + 1e-9)) * np.sqrt(252)

        return {
            "initial_capital": self.initial_capital,
            "final_equity": final_equity,
            "net_profit": final_equity - self.initial_capital,
            "total_return_pct": total_return_pct,
            "benchmark_return_pct": benchmark_return_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe_ratio,
            "total_trades": total_trades,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate_pct": win_rate,
            "profit_factor": profit_factor,
            "completed_trades": self.completed_trades,
            "equity_df": df_eq
        }
