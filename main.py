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
    
    buy_setups = []
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

        # 3. If BUY signal and not in strict capital preservation (BEARISH)
        if analysis["signal"] == "BUY" and regime != "BEARISH":
            # Run Risk position sizing
            pos_size = risk_engine.calculate_position_size(
                total_capital=capital,
                entry_price=analysis["close"],
                stop_loss_price=analysis["suggested_sl"]
            )
            
            if pos_size and pos_size["quantity"] > 0:
                buy_setups.append({
                    "symbol": symbol,
                    "name": name,
                    "close": analysis["close"],
                    "rsi": analysis["rsi"],
                    "suggested_sl": analysis["suggested_sl"],
                    "suggested_target": analysis["suggested_target"],
                    "quantity": pos_size["quantity"],
                    "investment": pos_size["total_investment"],
                    "pct_portfolio": pos_size["pct_of_portfolio"] * 100
                })
        else:
            # Other signals (HOLD / WAIT)
            logger.info(f"Analyzed {symbol}: Signal = {analysis['signal']} (Score: {analysis.get('score', 0):.0f})")

    # 4. Display Results
    print("\n--- SHARIA NON-COMPLIANT STOCKS ---")
    if non_compliant:
        for stock in non_compliant:
            print(f"- {stock['symbol']} ({stock['name']}): Rejected - {stock['reason']}")
    else:
        print("None")

    print("\n--- DETECTED BUY SETUPS ---")
    if buy_setups:
        df_buys = pd.DataFrame(buy_setups)
        # Format table
        print(df_buys.to_string(index=False, formatters={
            "close": "{:,.2f}".format,
            "rsi": "{:,.1f}".format,
            "suggested_sl": "{:,.2f}".format,
            "suggested_target": "{:,.2f}".format,
            "quantity": "{:,}".format,
            "investment": "₹{:,.2f}".format,
            "pct_portfolio": "{:,.2f}%".format
        }))
    else:
        print("No BUY setups detected for the current parameters.")

    if skipped_or_failed:
        print("\n--- SKIPPED STOCKS (DATA INCOMPLETE) ---")
        for stock in skipped_or_failed:
            print(f"- {stock['symbol']}: {stock['reason']}")

if __name__ == "__main__":
    cli()
