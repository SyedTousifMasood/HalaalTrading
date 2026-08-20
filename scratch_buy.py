import os
import sys
import datetime
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hsts.broker.zerodha_free import ZerodhaFreeBroker
from hsts.journal import TradingJournal
import time

def execute_trade():
    load_dotenv()
    user_id = os.getenv("ZERODHA_USER_ID")
    password = os.getenv("ZERODHA_PASSWORD")
    totp_secret = os.getenv("ZERODHA_TOTP_SECRET")

    print("Connecting to Zerodha...")
    broker = ZerodhaFreeBroker(user_id=user_id, password=password, totp_secret=totp_secret)
    if not broker.authenticate():
        print("[FAILED] Authentication failed.")
        sys.exit(1)

    symbol = "THELEELA"
    qty = 4
    sl = 498.76
    target = 640.46

    print(f"\nPlacing CNC MARKET BUY order for {qty} shares of {symbol}...")
    order_res = broker.place_order(symbol=symbol, qty=qty, transaction_type="BUY", order_type="MARKET")
    print(f"Order Response: {order_res}")

    if not order_res or not order_res.get("order_id"):
        print("[FAILED] Order placement failed. Aborting.")
        sys.exit(1)

    order_id = order_res.get("order_id")
    
    # Wait for order to execute
    time.sleep(2)
    
    # Fetch execution price
    orders = broker.get_orders()
    execution_price = None
    for o in orders or []:
        if o.get("order_id") == order_id:
            execution_price = o.get("average_price")
            break
            
    if not execution_price or execution_price == 0:
        print("[WARNING] Could not find execution price. Using fallback market price.")
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(period="1d")
        execution_price = df["Close"].iloc[-1]
        
    print(f"Executed Price: {execution_price}")
    
    # Place GTT OCO
    print(f"\nPlacing GTT OCO for {symbol}...")
    gtt_res = broker.place_gtt(
        symbol=symbol,
        qty=qty,
        trigger_type="oco",
        trigger_values=[sl, target],
        limit_prices=[sl - 0.5, target],
        last_price=execution_price
    )
    print(f"GTT Response: {gtt_res}")
    
    # Log to Journal
    print("\nUpdating Trading Journal...")
    journal = TradingJournal()
    entry_date = datetime.date.today().strftime("%Y-%m-%d")
    
    try:
        journal.add_trade(
            symbol=symbol,
            name=symbol,
            entry_date=entry_date,
            qty=qty,
            buy_price=execution_price,
            suggested_entry=execution_price,
            target=target,
            stop_loss=sl,
            notes=f"Manual Override (Cash Only Regime). GTT Trigger: {gtt_res.get('trigger_id', 'UNKNOWN')}"
        )
        
        # Log charges
        buy_charges = round(qty * execution_price * 0.0012, 2)
        charge_notes = f"Brokerage & taxes on {symbol} BUY ({qty} qty @ {execution_price:.2f})"
        if not journal.capital_transaction_exists(charge_notes):
            journal.add_capital_transaction("WITHDRAWAL", buy_charges, notes=charge_notes)
            
        print("[SUCCESS] Trade logged to Trading Journal Ledger.")
    except Exception as je:
        print(f"[ERROR] Failed to update Trading Journal: {je}")
        
    print("\n[COMPLETE] Trade execution finished.")

if __name__ == "__main__":
    execute_trade()
