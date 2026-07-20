# HSTS v1.0 Core Engine Walkthrough

We have successfully built and verified the core components of the **Halal Swing & Trend System (HSTS) v1.0**.

## Key Achievements

1. **Python Environment Set Up:** Installed Python 3.11.9 using `winget` and installed all project dependencies (`yfinance`, `pandas`, `click`, etc.).
2. **Modular Architecture Implemented:**
   - **[sharia.py](file:///d:/HalalTrading/hsts/sharia.py):** Implements business screening (excluding sectors like conventional banks, insurance, and haram keywords) and quarterly AAOIFI financial ratio filters.
   - **[regime.py](file:///d:/HalalTrading/hsts/regime.py):** Implements market regime classification using Nifty 50 close price against 50 EMA and 200 EMA.
   - **[scanner.py](file:///d:/HalalTrading/hsts/scanner.py):** Analyzes stock prices and volume to generate entry signals, 2x ATR stop-loss, and 1:2 risk-reward target prices.
   - **[risk.py](file:///d:/HalalTrading/hsts/risk.py):** Calculates position sizing based on 1% portfolio risk per trade, with a max allocation cap of 20% of total capital.
3. **CLI Interface Created:**
   - Implemented a unified Command Line Interface in **[main.py](file:///d:/HalalTrading/main.py)**.
4. **Successful Execution Verified:**
   - Ran `py main.py scan` to scan the initial database.
   - The scanner correctly identified the broader market regime as **BEARISH** (Close: 24,334.30 vs 200 EMA: 24,483.53), entering capital preservation mode.
   - Programmatically rejected non-compliant stocks (`HDFCBANK`, `ITC`, `MUTHOOTFIN`) and successfully processed the pre-screened universe (`TCS`, `INFY`, `RELIANCE`).

## Next Actions
- [ ] Build the mock broker paper-trading engine (`hsts/broker/mock.py`) to simulate order executions.
- [ ] Implement historical backtesting engine (`hsts/backtest.py`).
