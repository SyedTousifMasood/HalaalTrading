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
# Open Trades Analysis Tables

Whenever you are asked to provide suggestions or analysis on **Open Trades**:
1. You MUST display the results in a tabular format with the following exact columns:
   - Symbol
   - Entry Price
   - Current Price
   - Sessions/Days (Format: Trading Sessions / Calendar Days from date of purchase)
   - Trade Health (Score 0-100 calculated as: ((Current Price - Stop Loss) / (Target - Stop Loss)) * 100)
   - Stop Loss
   - Target
   - P&L (INR)
   - P&L (%)
   - Action (e.g., HOLD, TRAIL SL, SQUARE OFF)
