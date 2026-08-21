---
name: mtm-tracking
description: Enforces updating the current market price of all open positions in the trading journal.
---

# MTM Price Tracking Rule

To ensure the user's Trading Journal always reflects accurate Mark-To-Market (MTM) valuations for open positions:
1. Whenever you sync Zerodha orders, run portfolio evaluations, or are asked to review the journal after market hours, you MUST run the `py main.py update-mtm` command.
2. This ensures the "Current Price" and "Unrealized PnL" columns in the Ledger are populated with the last closed trading session price.
