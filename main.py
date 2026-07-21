import sys
import os
import pandas as pd
import click
import logging

from hsts.utils import setup_logging
from hsts.sharia import ShariaScreeningEngine
from hsts.regime import MarketRegimeEngine
from hsts.scanner import TechnicalScanner
from hsts.risk import RiskManagementEngine
from hsts.journal import TradingJournal

logger = logging.getLogger("hsts.main")

@click.group()
def cli():
    """HSTS: Halal Swing & Trend System v1.0 CLI"""
    setup_logging()

@cli.command()
@click.option("--capital", default=100000.0, help="Total available portfolio capital in INR.")
def scan(capital):
    """Scan stock universe for Sharia compliance and swing trading entries."""
    logger.info("Starting HSTS scanner run...")
    
    # 1. Load universe
    universe_path = "data/universe.csv"
    if not os.path.exists(universe_path):
        logger.error(f"Stock universe file not found at {universe_path}")
        sys.exit(1)
        
    sharia_engine = ShariaScreeningEngine(universe_path)
    regime_engine = MarketRegimeEngine()
    scanner = TechnicalScanner()
    risk_engine = RiskManagementEngine()

    # 2. Check Market Regime
    regime, regime_metrics = regime_engine.get_market_regime()
    print(f"\n=========================================")
    print(f"BROADER MARKET REGIME: {regime}")
    print(f"=========================================\n")

    if regime == "BEARISH":
        logger.warning("Market is BEARISH. Capital preservation mode active. No new momentum entries allowed.")
        # We can still screen for compliance and run tracking, but don't suggest new buys
        
    # 3. Screen and scan stock list
    df_universe = pd.read_csv(universe_path)
    
    all_compliant_analyses = []
    skipped_or_failed = []
    non_compliant = []
    
    print("Running screening and analysis...")
    for idx, row in df_universe.iterrows():
        symbol = row["symbol"]
        name = row["name"]
        
        # 1. Sharia Screening
        is_halal, screen_details = sharia_engine.screen_stock(symbol)
        if not is_halal:
            if screen_details.get("status") == "Data Fetch Failed":
                skipped_or_failed.append({
                    "symbol": symbol, 
                    "reason": "Sharia data fetch failed (possible network issue or invalid ticker)"
                })
            else:
                non_compliant.append({
                    "symbol": symbol,
                    "name": name,
                    "reason": screen_details.get("reason", "Unknown ratio violation")
                })
            continue

        # 2. Technical Scanner Analysis
        analysis = scanner.analyze_stock(symbol)
        if "reason" in analysis and analysis["signal"] == "WAIT" and "No historical" in analysis["reason"]:
            skipped_or_failed.append({"symbol": symbol, "reason": analysis["reason"]})
            continue

        # Collect all compliant stocks for ranking
        all_compliant_analyses.append({
            "symbol": symbol,
            "name": name,
            "close": analysis["close"],
            "rsi": analysis["rsi"],
            "score": analysis["score"],
            "signal": analysis["signal"],
            "suggested_sl": analysis["suggested_sl"],
            "suggested_target": analysis["suggested_target"]
        })

    # 4. Display Results
    print("\n--- SHARIA NON-COMPLIANT STOCKS ---")
    if non_compliant:
        for stock in non_compliant:
            print(f"- {stock['symbol']} ({stock['name']}): Rejected - {stock['reason']}")
    else:
        print("None")

    # Rank and display top 5 stocks by technical momentum score
    print("\n=========================================")
    print("TOP 5 COMPLIANT STOCKS BY MOMENTUM SCORE")
    print("=========================================")
    if all_compliant_analyses:
        df_all = pd.DataFrame(all_compliant_analyses)
        df_top5 = df_all.sort_values(by="score", ascending=False).head(5)
        
        # Calculate mock position size for top 5 for illustration
        buy_setups = []
        for _, row in df_top5.iterrows():
            pos_size = risk_engine.calculate_position_size(
                total_capital=capital,
                entry_price=row["close"],
                stop_loss_price=row["suggested_sl"]
            )
            buy_setups.append({
                "Symbol": row["symbol"],
                "Name": row["name"],
                "Close": row["close"],
                "Score": f"{row['score']:.0f}/100",
                "Signal": row["signal"],
                "Stop Loss": row["suggested_sl"],
                "Target": row["suggested_target"],
                "Qty": pos_size["quantity"] if pos_size else 0,
                "Allocation": f"INR {pos_size['total_investment']:,.2f}" if pos_size else "INR 0.00"
            })
        
        df_display = pd.DataFrame(buy_setups)
        print(df_display.to_string(index=False))
        
        if regime == "BEARISH":
            print("\n> [!WARNING]")
            print("> Market regime is BEARISH. These setups are for informational/monitoring purposes only.")
            print("> Under HSTS rule-based guidelines, trading these is strictly not recommended today.")

        # Log recommendations to Google Sheets Trading Journal
        try:
            journal = TradingJournal()
            for _, row in df_top5.iterrows():
                pos_size = risk_engine.calculate_position_size(
                    total_capital=capital,
                    entry_price=row["close"],
                    stop_loss_price=row["suggested_sl"]
                )
                qty = pos_size["quantity"] if pos_size else 0
                alloc = pos_size["total_investment"] if pos_size else 0.0
                exec_status = "SKIPPED_BEARISH_REGIME" if regime == "BEARISH" else "PENDING"
                
                journal.add_recommendation(
                    symbol=row["symbol"],
                    name=row["name"],
                    score=row["score"],
                    target_entry=row["close"],
                    stop_loss=row["suggested_sl"],
                    profit_target=row["suggested_target"],
                    qty=qty,
                    allocation=alloc,
                    status=exec_status,
                    notes=f"Scanned under {regime} regime"
                )
            print("\nSuccessfully logged top recommendations to Google Sheets journal!")
        except Exception as e:
            logger.error(f"Error logging recommendations to journal: {e}")
    else:
        print("No compliant stocks analyzed.")

    if skipped_or_failed:
        print("\n--- SKIPPED STOCKS (DATA INCOMPLETE) ---")
        for stock in skipped_or_failed:
            print(f"- {stock['symbol']}: {stock['reason']}")

@cli.command()
def journal_init():
    """Initialize the Google Sheets/Excel Trading Journal."""
    try:
        TradingJournal()
        print("Trading Journal spreadsheet initialized successfully on Google Drive!")
    except Exception as e:
        print(f"Error initializing journal: {e}")

@cli.command()
@click.argument("symbol")
@click.argument("qty", type=int)
@click.argument("buy_price", type=float)
@click.option("--notes", default="", help="Optional trade execution notes.")
def journal_add(symbol, qty, buy_price, notes):
    """Record a buy trade entry into the Ledger."""
    try:
        import datetime
        # Load from universe to get name
        universe_path = "data/universe.csv"
        name = "Unknown Stock"
        if os.path.exists(universe_path):
            df = pd.read_csv(universe_path)
            matched = df[df["symbol"] == symbol.upper()]
            if not matched.empty:
                name = matched.iloc[0]["name"]
                
        # Generate technical scanner values for comparison
        scanner = TechnicalScanner()
        analysis = scanner.analyze_stock(symbol.upper())
        suggested_entry = analysis.get("close", buy_price)
        suggested_sl = analysis.get("suggested_sl", buy_price * 0.95)
        suggested_target = analysis.get("suggested_target", buy_price * 1.10)

        entry_date = datetime.date.today().strftime("%Y-%m-%d")

        journal = TradingJournal()
        journal.add_trade(
            symbol=symbol.upper(),
            name=name,
            entry_date=entry_date,
            qty=qty,
            buy_price=buy_price,
            suggested_entry=suggested_entry,
            target=suggested_target,
            stop_loss=suggested_sl,
            notes=notes
        )
        print(f"Successfully recorded buy entry for {symbol.upper()} ({qty} shares at INR {buy_price:.2f})")
    except Exception as e:
        print(f"Error adding trade: {e}")

@cli.command()
@click.argument("symbol")
@click.argument("exit_price", type=float)
@click.argument("status", type=click.Choice(["win", "loss", "WIN", "LOSS"]))
@click.option("--notes", default="", help="Optional trade exit notes.")
def journal_close(symbol, exit_price, status, notes):
    """Close an open trade in the Ledger and record performance."""
    try:
        import datetime
        exit_date = datetime.date.today().strftime("%Y-%m-%d")
        journal = TradingJournal()
        success = journal.close_trade(
            symbol=symbol.upper(),
            exit_date=exit_date,
            exit_price=exit_price,
            status=status,
            notes=notes
        )
        if success:
            print(f"Successfully closed trade for {symbol.upper()} at INR {exit_price:.2f} ({status.upper()})")
        else:
            print(f"Could not find an active open trade for {symbol.upper()} to close.")
    except Exception as e:
        print(f"Error closing trade: {e}")

@cli.command()
@click.argument("amount", type=float)
@click.option("--notes", default="", help="Optional deposit notes.")
def journal_deposit(amount, notes):
    """Record a capital deposit (investment) into the account."""
    try:
        journal = TradingJournal()
        journal.add_capital_transaction("DEPOSIT", amount, notes)
        print(f"Successfully recorded deposit of INR {amount:,.2f} to Capital.")
    except Exception as e:
        print(f"Error logging deposit: {e}")

@cli.command()
@click.argument("amount", type=float)
@click.option("--notes", default="", help="Optional withdrawal notes.")
def journal_withdraw(amount, notes):
    """Record a capital withdrawal from the account."""
    try:
        journal = TradingJournal()
        journal.add_capital_transaction("WITHDRAWAL", amount, notes)
        print(f"Successfully recorded withdrawal of INR {amount:,.2f} from Capital.")
    except Exception as e:
        print(f"Error logging withdrawal: {e}")

@cli.command()
def connect_zerodha():
    """Connect to Zerodha Kite account using credentials from .env file."""
    try:
        from dotenv import load_dotenv
        from hsts.broker.zerodha_free import ZerodhaFreeBroker
        
        load_dotenv()
        user_id = os.getenv("ZERODHA_USER_ID")
        password = os.getenv("ZERODHA_PASSWORD")
        totp_secret = os.getenv("ZERODHA_TOTP_SECRET")
        
        if not user_id or not password or not totp_secret:
            print("[ERROR] Zerodha credentials missing in .env file!")
            print("Please edit d:\\HalalTrading\\.env and populate:")
            print("  ZERODHA_USER_ID=your_id")
            print("  ZERODHA_PASSWORD=your_password")
            print("  ZERODHA_TOTP_SECRET=your_totp_secret")
            return

        broker = ZerodhaFreeBroker(user_id=user_id, password=password, totp_secret=totp_secret)
        success = broker.authenticate()
        if success:
            print("\n[SUCCESS] Connected to Zerodha Kite account successfully!")
            margins = broker.get_margins()
            if margins:
                equity = margins.get("equity", {}).get("net", 0.0)
                print(f"Available Trading Margin: INR {equity:,.2f}")
        else:
            print("[FAILED] Zerodha connection failed. Check your User ID, Password, or TOTP Secret.")
    except Exception as e:
        print(f"[ERROR] Exception while connecting to Zerodha: {e}")

@cli.command()
def sync_zerodha_orders():
    """Fetch today's Zerodha orders and sync them with the Trading Journal Ledger."""
    try:
        import datetime
        from dotenv import load_dotenv
        from hsts.broker.zerodha_free import ZerodhaFreeBroker
        
        load_dotenv()
        user_id = os.getenv("ZERODHA_USER_ID")
        password = os.getenv("ZERODHA_PASSWORD")
        totp_secret = os.getenv("ZERODHA_TOTP_SECRET")
        
        if not user_id or not password or not totp_secret:
            print("[ERROR] Zerodha credentials missing in .env file!")
            return

        broker = ZerodhaFreeBroker(user_id=user_id, password=password, totp_secret=totp_secret)
        if not broker.authenticate():
            print("[FAILED] Authentication to Zerodha failed.")
            return

        orders = broker.get_orders()
        print(f"\n=========================================")
        print(f"FETCHED TODAY'S ZERODHA ORDERS ({len(orders)} total)")
        print(f"=========================================")

        if not orders:
            print("No orders were placed today in your Zerodha account.")
            return

        journal = TradingJournal()
        scanner = TechnicalScanner()

        synced_count = 0
        order_list = []
        for order in orders:
            symbol = order.get("tradingsymbol", "UNKNOWN")
            status = order.get("status", "UNKNOWN")
            tx_type = order.get("transaction_type", "BUY")
            qty = order.get("quantity", 0)
            avg_price = order.get("average_price", 0.0) or order.get("price", 0.0)
            order_time = order.get("order_timestamp", "")

            order_list.append({
                "Symbol": symbol,
                "Type": tx_type,
                "Qty": qty,
                "Price": avg_price,
                "Status": status,
                "Timestamp": order_time
            })

            # Auto-sync completed orders to Journal
            if status == "COMPLETE":
                if tx_type == "BUY":
                    # Fetch scanner values for comparison
                    analysis = scanner.analyze_stock(symbol)
                    suggested_entry = analysis.get("close", avg_price)
                    suggested_sl = analysis.get("suggested_sl", avg_price * 0.95)
                    suggested_target = analysis.get("suggested_target", avg_price * 1.10)
                    
                    journal.add_trade(
                        symbol=symbol,
                        name=symbol,
                        entry_date=datetime.date.today().strftime("%Y-%m-%d"),
                        qty=qty,
                        buy_price=avg_price,
                        suggested_entry=suggested_entry,
                        target=suggested_target,
                        stop_loss=suggested_sl,
                        notes="Auto-synced from Zerodha account"
                    )
                    synced_count += 1

                elif tx_type == "SELL":
                    journal.close_trade(
                        symbol=symbol,
                        exit_date=datetime.date.today().strftime("%Y-%m-%d"),
                        exit_price=avg_price,
                        status="WIN",
                        notes="Auto-synced sell from Zerodha account"
                    )
                    synced_count += 1

        df_orders = pd.DataFrame(order_list)
        print(df_orders.to_string(index=False))
        print(f"\n[SUCCESS] Synced {synced_count} completed trade(s) to Trading Journal Ledger!")

    except Exception as e:
        print(f"[ERROR] Exception while syncing Zerodha orders: {e}")

@cli.command()
@click.option("--period", default="1y", help="Historical simulation period (e.g. 6mo, 1y, 2y).")
@click.option("--capital", default=100000.0, help="Initial simulation capital.")
@click.option("--risk", default=0.01, help="Max portfolio risk per trade (e.g. 0.01 for 1%).")
@click.option("--ignore-regime", is_flag=True, help="Disable market regime filter and trade all setups regardless of market trend.")
@click.option("--start-date", default=None, help="Custom start date (YYYY-MM-DD).")
@click.option("--end-date", default=None, help="Custom end date (YYYY-MM-DD).")
def backtest(period, capital, risk, ignore_regime, start_date, end_date):
    """Run historical backtest simulation of HSTS v1.0 strategy."""
    try:
        from hsts.backtest import BacktestEngine
        engine = BacktestEngine(initial_capital=capital, max_risk_per_trade=risk)
        results = engine.run_backtest(period=period, ignore_regime=ignore_regime, start_date=start_date, end_date=end_date)
        
        if not results:
            print("[ERROR] Backtest run failed or no data available.")
            return

        print("\n=========================================")
        print(f"HSTS v1.0 HISTORICAL BACKTEST PERFORMANCE ({period.upper()})")
        print("=========================================")
        print(f"Initial Capital:         INR {results['initial_capital']:,.2f}")
        print(f"Final Equity:            INR {results['final_equity']:,.2f}")
        print(f"Net Profit / Loss:       INR {results['net_profit']:,.2f}")
        print(f"HSTS Strategy Return:    {results['total_return_pct']:.2f}%")
        print(f"Nifty 50 Benchmark:      {results['benchmark_return_pct']:.2f}%")
        print(f"Max Drawdown:            {results['max_drawdown_pct']:.2f}%")
        print(f"Sharpe Ratio:            {results['sharpe_ratio']:.2f}")
        print(f"Win Rate:                {results['win_rate_pct']:.1f}% ({results['win_count']} Wins / {results['loss_count']} Losses)")
        print(f"Profit Factor:           {results['profit_factor']:.2f}")
        print(f"Total Completed Trades:  {results['total_trades']}")
        
        if results['completed_trades']:
            print("\n--- SAMPLE RECENT COMPLETED TRADES ---")
            df_trades = pd.DataFrame(results['completed_trades']).tail(5)
            print(df_trades[["symbol", "entry_date", "entry_price", "exit_date", "exit_price", "pnl", "status"]].to_string(index=False))

    except Exception as e:
        print(f"[ERROR] Exception during backtesting: {e}")

@cli.command()
@click.option("--period", default="1y", help="Historical training period (e.g. 1y, 2y).")
@click.option("--start-date", default=None, help="Custom start date (YYYY-MM-DD).")
@click.option("--end-date", default=None, help="Custom end date (YYYY-MM-DD).")
def optimize_ai(period, start_date, end_date):
    """Train the Self-Learning AI Engine to optimize category indicator weights."""
    try:
        from hsts.ai_optimizer import AIOptimizerEngine
        optimizer = AIOptimizerEngine()
        config = optimizer.train_from_backtest(period=period, start_date=start_date, end_date=end_date)
        
        if not config:
            print("[ERROR] AI Optimization training failed.")
            return

        print("\n=========================================")
        print("HSTS SELF-LEARNING AI OPTIMIZATION REPORT")
        print("=========================================")
        print(f"Training Samples:        {config['training_samples_count']} historical trades")
        print(f"Last Trained:            {config['last_trained_timestamp']}")
        print(f"Historical Win Rate:     {config['win_rate_trained']:.1f}%")
        print("\n--- AI OPTIMIZED CATEGORY WEIGHTS ---")
        for cat, weight in config['category_weights'].items():
            print(f"  - {cat.capitalize():<12}: {weight*100:.1f}% (Weight multiplier: {weight:.4f})")
            
        print("\n[SUCCESS] AI Policy saved to config/ai_weights.json. Scanner will now use these refined weights!")

    except Exception as e:
        print(f"[ERROR] Exception during AI optimization: {e}")

if __name__ == "__main__":
    cli()
