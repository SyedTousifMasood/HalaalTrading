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
3. **Verify Open Positions:**
   - Run a check to ensure that all `OPEN` positions in the journal match the actual open holdings in the broker account. (Resolve any discrepancies like closed positions showing as open).
4. **Tally & Update:**
   - Run `py apply_reconciliation_and_styling.py` to finalize the dashboard metrics.
   - Commit and push the `Trading_Journal.xlsx` to GitHub.
