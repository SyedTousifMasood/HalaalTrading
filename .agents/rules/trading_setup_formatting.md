---
description: Formatting constraints for presenting trading setups to the user
---

# Trading Setup Tables

Whenever you present a table of trading setups or stock recommendations to the user:
1. You MUST always include the following unified set of columns in your tables (for both Swing and Intraday setups):
   - Symbol (and Name if appropriate)
   - Composite Score (or AI Score)
   - Entry Price / CMP
   - Stop Loss
   - Profit Target
   - Projected Profit %
   - Risk-to-Reward
   - Qty (calculated based on max allocation limits if needed)
   - Allocation (calculated based on max allocation limits if needed)

2. To calculate "Projected Profit %": `((Profit Target - Entry Price) / Entry Price) * 100`. Format it as a percentage with two decimal places (e.g., `12.15%`).

3. Ensure that NO columns are omitted from the scanner output. If the scanner misses metrics like Risk-to-Reward or Allocation, you MUST calculate them manually and include them.
