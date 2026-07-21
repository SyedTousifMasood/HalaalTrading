# HSTS v1.0 Core Engine & Trading Journal Walkthrough

We have successfully implemented and verified the core components of the **Halal Swing & Trend System (HSTS) v1.0**, including programmatic Sharia screening, 20+ indicator scanning, Google Sheets journal synchronization, and zero-cost broker integrations.

## Key Achievements

1. **Python Environment Set Up:** Installed Python 3.11.9 using `winget` and installed all project dependencies (`yfinance`, `pandas`, `openpyxl`, `pyotp`, `click`, etc.).
2. **Modular Architecture Implemented:**
   - **[sharia.py](file:///d:/HalalTrading/hsts/sharia.py):** Implements business screening (excluding conventional finance, tobacco, alcohol, etc.) and quarterly AAOIFI financial ratio checks.
   - **[regime.py](file:///d:/HalalTrading/hsts/regime.py):** Implements market regime classification using Nifty 50 close price against 50 EMA and 200 EMA.
   - **[scanner.py](file:///d:/HalalTrading/hsts/scanner.py):** Analyzes stocks across 20+ technical indicators (RSI, MACD, Stochastic, Bollinger Bands, Keltner Channels, Supertrend, OBV, VWAP, Pivot Points, Fibonacci levels, Candlestick shapes, and Order Blocks) to output a weighted momentum score (0-100).
   - **[risk.py](file:///d:/HalalTrading/hsts/risk.py):** Calculates position sizing based on 1% portfolio risk per trade, with a max allocation cap of 20% of total capital.
3. **Broker Adapters Implemented:**
   - **[base.py](file:///d:/HalalTrading/hsts/broker/base.py):** Unified broker interface for trade routing.
   - **[mock.py](file:///d:/HalalTrading/hsts/broker/mock.py):** Simulated paper-trading ledger requiring no credentials.
   - **[zerodha_free.py](file:///d:/HalalTrading/hsts/broker/zerodha_free.py):** Zero-cost Zerodha Kite Connect adapter utilizing TOTP 2FA (`pyotp`) auto-login to extract `enctoken` without requiring the ₹2,000/month API subscription fee.
4. **Google Sheets / Excel Trading Journal (`hsts/journal.py`):**
   - Creates and updates `G:\My Drive\HalaalTrading\Trading_Journal.xlsx` (syncs to Google Drive).
   - **Dashboard Sheet:** Computes Lifetime PnL, Win Rate, and trade metrics using live Excel formulas.
   - **Recommendations Sheet:** Automatically records daily top 5 setups with Risk-to-Reward Ratios (`1:2.0`) for audit comparison vs actual trades.
   - **Ledger Sheet:** Detailed ledger tracking Entry Price, Date, Qty, Target, Stop Loss, Exit Price, Exit Date, Status (WIN/LOSS/OPEN), realized P&L, and **Slippage/Deviation**.

## Next Actions
- [ ] Build backtesting engine (`hsts/backtest.py`).
