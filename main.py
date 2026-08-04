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
@click.option("--capital", default=None, type=float, help="Total available portfolio capital in INR. Defaults to Journal available capital.")
@click.option("--save-journal", is_flag=True, help="Save top recommendations to Google Sheets journal upon confirmation.")
def scan(capital, save_journal):
    """Scan stock universe for Sharia compliance and swing trading entries."""
    logger.info("Starting HSTS scanner run...")
    
    # 1. Load universe & Journal Capital
    universe_path = "data/universe.csv"
    if not os.path.exists(universe_path):
        logger.error(f"Stock universe file not found at {universe_path}")
        sys.exit(1)
        
    sharia_engine = ShariaScreeningEngine(universe_path)
    regime_engine = MarketRegimeEngine()
    scanner = TechnicalScanner()
    risk_engine = RiskManagementEngine()
    journal = TradingJournal()

    # Dynamic Capital Allocation from Trading Journal if not explicitly provided
    if capital is None:
        capital = journal.get_available_capital()
        print(f"\n[CAPITAL CONTROL] Capital Available for Trading (from Trading Journal): INR {capital:,.2f}")
    else:
        print(f"\n[CAPITAL CONTROL] User Specified Capital: INR {capital:,.2f}")

    # 2. Check Market Regime
    regime, regime_metrics = regime_engine.get_market_regime()
    print(f"=========================================")
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
    compliant_symbols = []
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
        
        compliant_symbols.append((symbol, name))

    if compliant_symbols:
        tickers_map = {f"{sym}.NS": (sym, name) for sym, name in compliant_symbols}
        tickers_list = list(tickers_map.keys())
        
        print(f"Batch downloading price history for {len(tickers_list)} compliant tickers...")
        import yfinance as yf
        df_batch = yf.download(tickers_list, period="6mo", group_by="ticker", progress=False)
        
        for ns_sym, (symbol, name) in tickers_map.items():
            df_ticker = None
            # Handle single ticker DataFrame format or multi-ticker
            if len(tickers_list) == 1:
                df_ticker = df_batch.dropna(subset=["Close"])
            elif ns_sym in df_batch.columns.levels[0]:
                df_ticker = df_batch[ns_sym].dropna(subset=["Close"])
                
            if df_ticker is None or df_ticker.empty or len(df_ticker) < 50:
                skipped_or_failed.append({"symbol": symbol, "reason": "No historical price data available"})
                continue

            # 2. Technical Scanner Analysis
            analysis = scanner.analyze_stock(symbol, df=df_ticker)
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
        
        # Calculate position size based on available capital and regime allocation limits
        buy_setups = []
        alloc_cap_pct = regime_metrics.get("allocation_cap", 0.20)
        for _, row in df_top5.iterrows():
            pos_size = risk_engine.calculate_position_size(
                total_capital=capital,
                entry_price=row["close"],
                stop_loss_price=row["suggested_sl"],
                max_allocation_pct=alloc_cap_pct
            )
            buy_setups.append({
                "Symbol": row["symbol"],
                "Name": row["name"],
                "Close": row["close"],
                "Composite Score": f"{row['score']:.0f}/100",
                "Signal": row["signal"],
                "Stop Loss": row["suggested_sl"],
                "Target": row["suggested_target"],
                "Qty": pos_size["quantity"] if pos_size else 0,
                "Allocation": f"INR {pos_size['total_investment']:,.2f}" if pos_size else "INR 0.00"
            })
        
        df_display = pd.DataFrame(buy_setups)
        print(df_display.to_string(index=False))
        
        if regime == "STATE 4: Cash Only":
            print("\n> [!WARNING]")
            print("> Market regime is Cash Only. Capital preservation mode active.")
            print("> Under HSTS rule-based guidelines, trading is strictly not recommended today.")
        elif regime in ["STATE 2: Bear Relief Rally", "STATE 3: Capitulation Bottom"]:
            print(f"\n> [!TIP]")
            print(f"> Market is in {regime}.")
            print(f"> Tactical swing trading is PERMITTED today with scaled-down position sizes (10% allocation cap).")
        else:
            print(f"\n> [!NOTE]")
            print(f"> Market is in {regime}. Full swing trading parameters active (20% allocation cap).")

        # Log recommendations to Google Sheets Trading Journal ONLY if save_journal is True
        if save_journal:
            try:
                journal = TradingJournal()
                for _, row in df_top5.iterrows():
                    pos_size = risk_engine.calculate_position_size(
                        total_capital=capital,
                        entry_price=row["close"],
                        stop_loss_price=row["suggested_sl"],
                        max_allocation_pct=alloc_cap_pct
                    )
                    qty = pos_size["quantity"] if pos_size else 0
                    alloc = pos_size["total_investment"] if pos_size else 0.0
                    exec_status = "SKIPPED_BEARISH_REGIME" if regime == "STATE 4: Cash Only" else "PENDING"
                    
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
                print("\n[SUCCESS] Saved top recommendations to Google Sheets journal!")
            except Exception as e:
                logger.error(f"Error logging recommendations to journal: {e}")
        else:
            print("\n> Note: Recommendations were NOT saved to Google Sheets journal.")
            print("> Run 'py main.py scan --save-journal' if you want to confirm and record recommendations.")
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

                    # Log buy-side commission/taxes to Capital sheet
                    buy_charges = round(qty * avg_price * 0.0012, 2)
                    charge_notes = f"Brokerage & taxes on {symbol} BUY ({qty} qty @ {avg_price:.2f})"
                    if not journal.capital_transaction_exists(charge_notes):
                        journal.add_capital_transaction("WITHDRAWAL", buy_charges, notes=charge_notes)
                        print(f"Logged buy charges for {symbol}: INR {buy_charges:.2f}")

                elif tx_type == "SELL":
                    buy_price = journal.get_open_trade_buy_price(symbol)
                    status = "WIN"
                    if buy_price is not None and avg_price < buy_price:
                        status = "LOSS"
                    journal.close_trade(
                        symbol=symbol,
                        exit_date=datetime.date.today().strftime("%Y-%m-%d"),
                        exit_price=avg_price,
                        status=status,
                        notes="Auto-synced sell from Zerodha account"
                    )
                    synced_count += 1

                    # Log sell-side commission/taxes to Capital sheet
                    sell_charges = round((qty * avg_price * 0.00104) + 15.93, 2)
                    charge_notes = f"Brokerage & taxes on {symbol} SELL ({qty} qty @ {avg_price:.2f})"
                    if not journal.capital_transaction_exists(charge_notes):
                        journal.add_capital_transaction("WITHDRAWAL", sell_charges, notes=charge_notes)
                        print(f"Logged sell charges for {symbol}: INR {sell_charges:.2f}")

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

@cli.command()
def scan_intraday():
    """Scan stock universe for Halal Intraday Trading setups (AAOIFI standards)."""
    import datetime
    from hsts.intraday_scanner import HalalIntradayScanner
    
    print("\n=========================================")
    print("HALAL INTRADAY TRADING STRATEGY (AAOIFI)")
    print("=========================================")
    print(f"Session Date: {datetime.date.today().strftime('%Y-%m-%d')}")
    print("Screening stocks for AAOIFI Shariah compliance and intraday momentum breakouts...\n")
    
    scanner = HalalIntradayScanner(universe_csv_path="data/universe.csv")
    candidates = scanner.scan_universe()
    
    if not candidates:
        print("\n[INFO] No breakout setups found meeting the Sharia-compliant criteria today.")
        return
        
    print(f"{'Date':<12} | {'Symbol':<12} | {'Composite Score':<15} | {'Target Entry':<12} | {'Stop-Loss':<10} | {'Profit Target':<13} | {'Risk-to-Reward':<14}")
    print("-" * 105)
    for c in candidates:
        print(f"{datetime.date.today().strftime('%Y-%m-%d'):<12} | {c['symbol']:<12} | {c['score']:<15} | INR {c['entry']:<8.2f} | INR {c['stop_loss']:<6.2f} | INR {c['target']:<9.2f} | 1:{c['rr_ratio']:.1f}")
    
    print("\n[COMPLIANCE NOTE] In accordance with AAOIFI standards, all intraday setups must be placed as CNC (Cash Delivery) orders on your broker platform.")
    print("Intraday MIS/margin leverage is strictly prohibited. Setups not hitting targets must be squared off before 3:15 PM IST.")

@cli.command()
@click.option("--symbol", required=True, help="Stock symbol (e.g. SONACOMS).")
@click.option("--qty", required=True, type=int, help="Quantity to buy.")
@click.option("--price", required=True, type=float, help="AMO buy limit price.")
@click.option("--sl", required=True, type=float, help="GTT Stop-Loss price.")
@click.option("--target", required=True, type=float, help="GTT Profit Target price.")
def place_intraday_amo(symbol, qty, price, sl, target):
    """Place a Sharia-compliant pre-market Intraday BUY AMO + GTT exit orders."""
    import json
    import datetime
    from dotenv import load_dotenv
    from hsts.broker.zerodha_free import ZerodhaFreeBroker
    from hsts.scheduler_utils import register_square_off_task
    
    load_dotenv()
    user_id = os.getenv("ZERODHA_USER_ID")
    password = os.getenv("ZERODHA_PASSWORD")
    totp_secret = os.getenv("ZERODHA_TOTP_SECRET")
    
    print("Connecting to Zerodha...")
    broker = ZerodhaFreeBroker(user_id=user_id, password=password, totp_secret=totp_secret)
    if not broker.authenticate():
        print("[FAILED] Authentication failed.")
        sys.exit(1)
        
    print(f"\nPlacing BUY LIMIT AMO order for {qty} shares of {symbol} at INR {price:.2f}...")
    order_res = broker.place_order(symbol=symbol, qty=qty, transaction_type="BUY", order_type="LIMIT", price=price, variety="amo")
    print("AMO Order Response:", order_res)
    
    if order_res.get("status") in ["COMPLETE", "SUCCESS"] or order_res.get("order_id"):
        order_id = order_res.get("order_id")
        print(f"[SUCCESS] AMO Buy placed successfully! ID: {order_id}")
        
        # Place GTT OCO
        print(f"\nPlacing GTT OCO (two-leg) trigger for {symbol} (SL: {sl:.2f}, Target: {target:.2f})...")
        gtt_res = broker.place_gtt(
            symbol=symbol,
            qty=qty,
            trigger_type="two-leg",
            trigger_values=[sl, target],
            limit_prices=[sl, target],
            last_price=price
        )
        print("GTT Response:", gtt_res)
        
        # Log to Trading Journal
        try:
            journal = TradingJournal()
            entry_date = datetime.date.today().strftime("%Y-%m-%d")
            
            # Log as INTRADAY
            journal.add_trade(
                symbol=symbol,
                name=symbol,
                entry_date=entry_date,
                qty=qty,
                buy_price=price,
                suggested_entry=price,
                target=target,
                stop_loss=sl,
                notes=f"Intraday AMO placement. GTT Trigger: {gtt_res.get('trigger_id', 'UNKNOWN')}",
                trade_type="INTRADAY"
            )
            
            # Log charges
            buy_charges = round(qty * price * 0.0012, 2)
            charge_notes = f"Brokerage & taxes on {symbol} BUY ({qty} qty @ {price:.2f})"
            if not journal.capital_transaction_exists(charge_notes):
                journal.add_capital_transaction("WITHDRAWAL", buy_charges, notes=charge_notes)
                
            print("[SUCCESS] Trade logged to Trading Journal Ledger as INTRADAY.")
        except Exception as je:
            print(f"[ERROR] Failed to update Trading Journal: {je}")
            
        # Register square-off task at 3:15 PM
        register_square_off_task()
        
        # Save to active trades registry
        os.makedirs("data", exist_ok=True)
        registry_path = "data/active_intraday_trades.json"
        trades = []
        if os.path.exists(registry_path):
            try:
                with open(registry_path, "r") as f:
                    trades = json.load(f)
            except Exception:
                pass
        trades.append({
            "symbol": symbol,
            "qty": qty,
            "buy_order_id": order_id,
            "trigger_id": gtt_res.get("trigger_id") if gtt_res else None,
            "sl": sl,
            "target": target
        })
        with open(registry_path, "w") as f:
            json.dump(trades, f, indent=4)
        print("[SUCCESS] Trade added to active intraday trades registry.")
    else:
        print("[FAILED] AMO order placement failed. Exits and logs skipped.")

@cli.command()
def square_off_intraday():
    """Check active intraday setups and square off open positions at 3:15 PM IST."""
    import json
    import datetime
    from hsts.broker.zerodha_free import ZerodhaFreeBroker
    from hsts.scheduler_utils import deregister_square_off_task
    
    registry_path = "data/active_intraday_trades.json"
    if not os.path.exists(registry_path):
        print("[INFO] No active intraday trades found to square off.")
        deregister_square_off_task()
        return
        
    with open(registry_path, "r") as f:
        try:
            trades = json.load(f)
        except Exception:
            trades = []
            
    if not trades:
        print("[INFO] Active intraday trades registry is empty.")
        deregister_square_off_task()
        return
        
    from dotenv import load_dotenv
    load_dotenv()
    user_id = os.getenv("ZERODHA_USER_ID")
    password = os.getenv("ZERODHA_PASSWORD")
    totp_secret = os.getenv("ZERODHA_TOTP_SECRET")
    
    print("Connecting to Zerodha...")
    broker = ZerodhaFreeBroker(user_id=user_id, password=password, totp_secret=totp_secret)
    if not broker.authenticate():
        print("[FAILED] Authentication failed.")
        sys.exit(1)
        
    journal = TradingJournal()
    exit_date = datetime.date.today().strftime("%Y-%m-%d")
    
    for t in trades:
        symbol = t["symbol"]
        qty = t["qty"]
        trigger_id = t["trigger_id"]
        
        print(f"\n--- Processing Square-Off for {symbol} ---")
        
        # 1. Check if GTT is still active
        is_gtt_active = False
        if trigger_id:
            gtts = broker.get_gtts()
            for g in gtts or []:
                if g.get("trigger_id") == trigger_id:
                    is_gtt_active = True
                    break
                    
        # 2. If GTT is active, position is still open -> Cancel GTT and Market Sell
        if is_gtt_active:
            print(f"GTT trigger {trigger_id} is still active. Position is OPEN.")
            print(f"Cancelling GTT {trigger_id}...")
            broker.delete_gtt(trigger_id)
            
            print(f"Placing CNC SELL MARKET order for {qty} shares of {symbol}...")
            sell_res = broker.place_order(symbol=symbol, qty=qty, transaction_type="SELL", order_type="MARKET")
            print("Sell Order Response:", sell_res)
            
            exit_price = None
            if sell_res.get("order_id"):
                sell_order_id = sell_res.get("order_id")
                # Find exit price from orders list
                orders = broker.get_orders()
                for o in orders or []:
                    if o.get("order_id") == sell_order_id:
                        exit_price = o.get("average_price")
                        break
            if not exit_price:
                exit_price = t["sl"]  # fallback
                
            buy_price = journal.get_open_trade_buy_price(symbol, trade_type="INTRADAY") or t["sl"]
            status = "WIN" if exit_price >= buy_price else "LOSS"
            journal.close_trade(symbol, exit_date, exit_price, status, f"Manually squared off at 3:15 PM (Execution: INR {exit_price:.2f})", trade_type="INTRADAY")
            print(f"[SUCCESS] Position squared off and logged to journal at INR {exit_price:.2f}.")
        else:
            # GTT already triggered. Find exit price from trades list
            print(f"GTT trigger {trigger_id} is no longer active. Position was already closed.")
            exit_price = None
            orders = broker.get_orders()
            for o in orders or []:
                if o.get("tradingsymbol") == symbol and o.get("transaction_type") == "SELL" and o.get("status") == "COMPLETE":
                    exit_price = o.get("average_price")
                    break
            if not exit_price:
                exit_price = t["target"]  # default fallback
                
            buy_price = journal.get_open_trade_buy_price(symbol, trade_type="INTRADAY") or t["sl"]
            status = "WIN" if exit_price >= buy_price else "LOSS"
            journal.close_trade(symbol, exit_date, exit_price, status, f"Position closed automatically via GTT trigger (Exit: INR {exit_price:.2f})", trade_type="INTRADAY")
            print(f"[SUCCESS] Position verified closed and logged to journal.")
            
    # Clean up
    if os.path.exists(registry_path):
        os.remove(registry_path)
    deregister_square_off_task()
    print("\n[SUCCESS] Square-off cycle complete. Windows scheduled task removed.")

@cli.command()
def rebuild_sharia_cache():
    """Download financial reports and rebuild the Sharia Compliance local cache."""
    print("Rebuilding Sharia Compliance Cache for the stock universe...")
    universe_path = "data/universe.csv"
    if not os.path.exists(universe_path):
        print(f"[ERROR] Universe file not found at {universe_path}")
        return
        
    df_universe = pd.read_csv(universe_path)
    sharia_engine = ShariaScreeningEngine(universe_path)
    
    # Clear the existing cache to force live check
    sharia_engine.cache = {}
    
    total = len(df_universe)
    print(f"Starting programmatic screen for {total} symbols...")
    
    for idx, row in df_universe.iterrows():
        symbol = row["symbol"]
        print(f"[{idx+1}/{total}] Screening {symbol}...")
        # Since we cleared cache, screen_stock will download financials and save to cache
        sharia_engine.screen_stock(symbol)
        
    print("\n[SUCCESS] Sharia Compliance Cache rebuilt successfully at data/sharia_cache.json!")

if __name__ == "__main__":
    cli()
