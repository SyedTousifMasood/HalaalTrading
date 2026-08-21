---
name: google-sheets-throttling
description: Enforces delays during multiple journal updates to prevent Google Sheets quota limits.
---

# Google Sheets Throttling Rule

When performing actions that write to or update `Trading_Journal.xlsx`, you MUST respect Google Sheets conversion quota limits to prevent the user from experiencing `QUOTA_EXCEEDED` / `AdaptiveThrottler` errors.

1. **Custom Scripts:** If you write a custom script (e.g., `execute_trades.py`) that loops through multiple trades and logs them to the journal, you MUST add a `time.sleep(5)` to `time.sleep(10)` between each individual `journal.add_trade()` call.
2. **Sequential Commands:** If you are running multiple CLI commands sequentially that all update the journal (e.g., closing a trade, adding a trade, syncing orders), do not run them simultaneously. Wait for one to fully complete before starting the next.
3. **Bulk Updates:** If an operation requires more than 3 continuous updates to the journal, pause the operation for 60 seconds (`time.sleep(60)`) midway through to allow Google's backend sync to cool down.
