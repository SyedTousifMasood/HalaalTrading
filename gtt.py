import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from hsts.broker.zerodha_free import ZerodhaFreeBroker

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
    sl = 498.75
    target = 640.45
    last_price = 539.30
    
    # Try with "two-leg"
    print(f"\nPlacing GTT OCO (two-leg) for {symbol}...")
    gtt_res = broker.place_gtt(
        symbol=symbol,
        qty=qty,
        trigger_type="two-leg",
        trigger_values=[sl, target],
        limit_prices=[sl - 0.5, target],
        last_price=last_price
    )
    print(f"GTT Response: {gtt_res}")

if __name__ == "__main__":
    execute_trade()
