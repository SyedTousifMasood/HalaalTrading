---
description: Comprehensive workflow to follow when asked to sync or update the trading journal.
---

# Comprehensive Sync Workflow

Whenever the user asks to "sync", "scan", or "update the trading journal", you MUST perform the following checks sequentially and tally them before concluding the task:

1. **Check Deposits/Withdrawals:** 
   - You must verify with the user or check the Zerodha account for any new capital deposits or withdrawals.
   - If there are new transactions, manually log them into the `Capital` sheet of `Trading_Journal.xlsx` (e.g., via a python script).
2. **Sync Executed Orders:**
   - Run `py main.py sync-zerodha-orders` to pull newly executed Intraday/Swing trades and stop-loss triggers.
3. **Verify Open Delivery Holdings (Anti-Phantom Position Check):**
   - You must ensure the script fetches live delivery holdings via the Zerodha API (`broker.get_holdings()`).
   - Cross-reference the live holdings against all `OPEN` trades in the Ledger.
   - If a stock is `OPEN` in the Journal but missing from live holdings, you MUST officially close it in the Ledger by setting its `Exit Date` and `Exit Price` to accurately log the `Realized PnL`.
4. **Tally & Update:**
   - Run `py apply_reconciliation_and_styling.py` to finalize the dashboard metrics.
5. **Strict End-of-Day Valuation Rule:**
   - **NEVER** overwrite the Dashboard's "Cash Available for Trading" with the live intraday Zerodha margin API.
   - The cash margin and portfolio valuation MUST be strictly calculated mathematically using the Ledger's formulas (Initial Capital + Deposits - Withdrawals - Deployed Capital + Realized PnL) and the previous session's closing prices, to prevent volatile T+1 settlement discrepancies.
   - Commit and push the `Trading_Journal.xlsx` to GitHub.
