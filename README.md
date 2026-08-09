# HSTS (Halal Trading System)

HSTS (Halal Trading System) is a systematic, rules-based momentum trading application designed for Indian equities. It combines rigorous AAOIFI Sharia-compliant screening with mathematical momentum indicators and a dynamic market regime engine.

---

## 1. System Overview & Core Pillars

### A. AAOIFI Sharia Compliance
HSTSConcentrates capital only on asset-backed, fundamentally sound, and ethical businesses by filtering out non-permissible sectors and highly leveraged companies:
*   **Business Exclusions:** Rejects conventional banks, NBFCs, conventional insurance, liquor, tobacco, casinos, and non-halal food.
*   **Financial Leverage Limits:**
    *   Debt-to-Assets ratio must be $< 33\%$.
    *   Interest-bearing cash-to-Assets ratio must be $< 33\%$.
    *   Receivables-to-Assets ratio must be $< 49\%$.
    *   Interest-bearing income must be $< 5\%$ of total revenue.
*   **Execution Safety:** Cash-delivery swing and intraday trading only. F&O leverage, derivative speculation, short-selling, and margin lending are strictly prohibited.

### B. Mathematical Momentum
*   **Trend Alignment:** Scans 536 pre-screened compliant equities to verify that the long-term price trend is positive (above the 200 EMA).
*   **Breakout Scoring:** Evaluates short-term momentum using a composite formula (RSI, ADX, MACD, and EMA crossovers) to generate a score from 0 to 100.
*   **Automation:** Integrates with Zerodha Kite to place limit entry orders and automatically register server-side protection brackets (GTT OCO) for targets and stop-losses.

---

## 2. Market Regimes & Exposure Curve

HSTS monitors the Nifty 50 Index (`^NSEI`) and market breadth to classify the broader market into 4 distinct states, dynamically adjusting capital exposure to protect portfolio equity:

*   **State 1: Macro Bullish** (Max 20% allocation per trade)
*   **State 2: Bear Relief Rally** (Max 10% allocation per trade)
*   **State 3: Capitulation Bottom** (Max 10% allocation per trade)
*   **State 4: Risk-Off / Cash** (0% allocation — 100% Capital preserved in Cash)

---

## 3. Market Type Definitions

The HSTS engine operates with precise definitions for different market conditions:

### A. Trending / Bullish Market
*   **General Definition:** A market exhibiting a sustained, directional upward move in prices characterized by a sequence of **Higher Highs (HH)** and **Higher Lows (HL)**. Participation is broad, and major moving averages slope upwards with shallow corrections.
*   **HSTS Codification:** Defined as **State 1 (Macro Bullish)**:
    1.  The Nifty 50 Index is trading above its 200-period EMA.
    2.  Market Breadth is $> 50\%$ (more than half of the Shariah universe is trading above their respective 20-period moving averages).

### B. Choppy / Sideways Market
*   **General Definition:** A range-bound market without a clear directional trend, where prices fluctuate between horizontal support and resistance levels. Characterized by frequent false breakouts ("bull traps"), flat moving averages, and rapid sector rotation.
*   **HSTS Codification:** Defined as **State 2 (Relief Rally / Consolidation)** or **State 4 (Risk-Off / Cash)**:
    1.  The Nifty 50 Index is trading below or flatlining around its 200 EMA.
    2.  Market Breadth is $< 50\%$, indicating a lack of broad-based participation.

---

## 4. HSTS vs. VTSS Regime Playbook Selection

Depending on the market type identified by the regime engine, HSTS toggles between two distinct execution playbooks:

### Playbook A: Standard HSTS Swing Setup (Bullish/Trending)
*   **Target Regime:** State 1 (Macro Bullish).
*   **Profit Target:** **10% to 15%** (to ride the full momentum wave).
*   **Stop-Loss:** **5% to 7.5%** (giving volatility breathing room).
*   **Max Allocation:** Up to **20%** per position.
*   **Time-Stop:** No time limits (held until exit brackets are triggered).

### Playbook B: Velocity-Tax Swing Strategy (VTSS) Setup (Sideways/Choppy)
*   **Target Regime:** State 2 or State 4 (Range-Bound / Chop).
*   **Profit Target:** **5% to 7%** (calculated dynamically as $1.5 \times \text{ATR}$).
*   **Stop-Loss:** **2.5% to 3.5%** (calculated dynamically as $0.75 \times \text{ATR}$ to keep drawdowns minimal).
*   **Max Positions:** Restricted to **3 to 4 concentrated positions** (25% to 33% capital each) to reduce CDSL depository fees.
*   **Time-Stop Policy:** Dynamic **5-Day Review** (exit early if the position is stagnant) and **7-Day Hard Exit** (liquidated at market close on the 7th session if targets/SLs are not hit).
*   **Execution Discipline:** Single-tranche buy and sell orders only (no partial scaling) and BTST exits when targets are hit within 48 hours to bypass Demat settlement costs.
