# HSTS v1.0 Core Engine & Trading Journal Walkthrough

We have successfully implemented and verified the core components of the **Halal Swing & Trend System (HSTS) v1.0**, including programmatic Sharia screening, 20+ indicator scanning, and Google Sheets journal synchronization.

## Key Achievements

1. **Python Environment Set Up:** Installed Python 3.11.9 using `winget` and installed all project dependencies (`yfinance`, `pandas`, `openpyxl`, `click`, etc.).
2. **Modular Architecture Implemented:**
   - **[sharia.py](file:///d:/HalalTrading/hsts/sharia.py):** Implements business screening (excluding conventional finance, tobacco, alcohol, etc.) and quarterly AAOIFI financial ratio checks.
   - **[regime.py](file:///d:/HalalTrading/hsts/regime.py):** Implements market regime classification using Nifty 50 close price against 50 EMA and 200 EMA.
   - **[scanner.py](file:///d:/HalalTrading/hsts/scanner.py):** Analyzes stocks across 20+ technical indicators (RSI, MACD, Stochastic, Bollinger Bands, Keltner Channels, Supertrend, OBV, VWAP, Pivot Points, Fibonacci levels, Candlestick shapes, and Order Blocks) to output a weighted momentum score (0-100).
   - **[risk.py](file:///d:/HalalTrading/hsts/risk.py):** Calculates position sizing based on 1% portfolio risk per trade, with a max allocation cap of 20% of total capital.
3. **Google Sheets / Excel Trading Journal (`hsts/journal.py`):**
   - Creates and updates `G:\My Drive\HalaalTrading\Trading_Journal.xlsx` (syncs to Google Drive).
   - **Dashboard Sheet:** Computes Lifetime PnL, Win Rate, and trade metrics using live Excel formulas.
   - **Ledger Sheet:** Detailed ledger tracking Entry Price, Date, Qty, Target, Stop Loss, Exit Price, Exit Date, Status (WIN/LOSS/OPEN), realized P&L, and **Slippage/Deviation** comparing actual entries to suggested levels.
   - **Logs Sheet:** Tracks system audit logs and action logs.

## Verification & Execution Logs
- **System run:** Executed `py main.py scan` to verify. The scanner correctly identified the broader market regime as **BEARISH** (Nifty 50 close: 24,334.30 vs 200 EMA: 24,483.53), entering capital preservation mode.
- **Top stocks scored:** TCS (90/100), HCLTECH (84/100), SUNPHARMA (83/100), TECHM (82/100), and DIVISLAB (76/100).
- **Journal commands verified:**
  * `py main.py journal-init` initialized the sheet.
  * `py main.py journal-add TCS 10 2269.00 --notes "Initial HSTS mock setup trade"` successfully logged the entry.
  * `py main.py journal-close TCS 2540.00 WIN --notes "Sold at target limit"` successfully logged the exit, calculating a net P&L of +INR 2,710.00.

## Next Actions
- [ ] Build paper trading broker adapter (`hsts/broker/mock.py`).
- [ ] Build backtesting engine (`hsts/backtest.py`).
