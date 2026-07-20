# Halal Swing & Trend System (HSTS) v1.0

This plan outlines the architecture and phased implementation of HSTS v1.0, a rule-based, Sharia-compliant swing trading system for Indian stock markets (NSE/BSE), focusing on cash delivery (CNC), risk management, and capital preservation.

## User Review Required

> [!IMPORTANT]
> Since Python was not found in the initial check, we will need to install Python (e.g., Python 3.11/3.12) via `winget` to run and test this system locally. 

> [!WARNING]
> Since we do not have live broker credentials yet, the initial version of HSTS will include a **Mock/Paper Trading Broker Adapter** so you can run the system, scan stocks, and simulate trades without risking real capital.

## Proposed Architecture & Directory Structure

We will create a modular, clean, and easily testable Python architecture inside the `d:\HalalTrading` workspace:

```
d:\HalalTrading\
├── hsts\
│   ├── __init__.py
│   ├── sharia.py       # Sharia compliance (Business & Financial filters)
│   ├── regime.py       # Market Regime Filter (Bullish/Neutral/Bearish)
│   ├── scanner.py      # Momentum Scanner & Technical Indicators
│   ├── risk.py         # Position sizing and Stop-loss calculations (ATR/EMA)
│   ├── portfolio.py    # Portfolio tracking & exposure limits
│   ├── backtest.py     # Backtesting engine for historical simulation
│   ├── broker\
│   │   ├── __init__.py
│   │   ├── base.py     # Abstract base class for broker adapters
│   │   ├── mock.py     # Simulated paper-trading broker
│   │   └── zerodha.py  # Mock/Placeholder Zerodha adapter
│   └── utils.py        # Config, logging, and helper functions
├── data\
│   └── sharia_universe.csv # List of Sharia-compliant stock symbols
├── main.py             # CLI runner script
├── requirements.txt    # Python dependencies (pandas, numpy, yfinance, etc.)
└── README.md           # System documentation
```

---

## Phase 1: Core System Components

### 1. Sharia Screening Engine (`hsts/sharia.py`)
- Reads a predefined Sharia-compliant stock list (e.g., from a CSV).
- Contains business and financial ratio rules to allow custom validation (e.g., Debt/Market Cap < 33%).

### 2. Market Regime Engine (`hsts/regime.py`)
- Evaluates the Nifty 50 or Nifty 500 index to classify the broader market regime: **Bullish**, **Neutral**, or **Bearish** (using moving averages like 200 EMA and index breadth).

### 3. Momentum Scanner & Technical Strategy (`hsts/scanner.py`)
- Fetches daily price data for the Sharia universe (using `yfinance` or a mock provider).
- Implements indicators (EMA crossovers, relative strength, volume breakout, ATR).
- Flags high-probability entry setups.

### 4. Position Sizing & Risk Engine (`hsts/risk.py`)
- Pre-calculates target quantity based on capital risk (e.g., risking max 1% of total portfolio per trade).
- Sets initial Stop-loss (ATR-based or Swing-Low) and tracks Trailing Stop-loss.

---

## Verification Plan

### Automated Verification
- We will write unit tests using `pytest` to verify Sharia filters, position sizing math, and indicator calculations.
- We will run a backtest simulation on a sample historical dataset.

### Manual Verification
- Run `main.py scan` to print a list of Sharia-compliant, regime-aligned momentum stocks.
- Run a paper-trade simulation.
