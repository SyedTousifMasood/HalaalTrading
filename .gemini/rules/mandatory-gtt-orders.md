---
name: mandatory-gtt-orders
description: Mandates the attachment of GTT OCO orders for every trade execution and specifies API syntax constraints.
---

# Mandatory GTT Orders Rule

Whenever you are tasked with executing a BUY or SELL order (e.g., via a custom Python script like `execute_trades.py`), you MUST always place a corresponding GTT order to protect the position.

**Strict API Constraints for ZerodhaFreeBroker:**
1. **Trigger Type:** You must use `trigger_type="two-leg"` (do NOT use `"oco"`) when calling `broker.place_gtt()`.
2. **Tick Size Rounding:** All `trigger_values` and `limit_prices` MUST be rounded to the nearest `0.05` tick size before being passed to the API to prevent "Invalid trigger data" errors. 
   - *Example Helper Function:* `round(round(price / 0.05) * 0.05, 2)`
3. **Validation:** Never assume the GTT order was successful without logging the response. If the GTT fails, alert the user immediately.
