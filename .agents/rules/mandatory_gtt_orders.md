---
description: Strict requirement to always place GTT orders with any new trade.
---

# Mandatory GTT Order Placement

Whenever you are instructed to place a new buy order (whether Intraday or Swing):
1. You MUST ALWAYS place the corresponding GTT (Good-Till-Triggered) order for the Target and Stop Loss immediately after the buy order.
2. This is COMPULSORY and cannot be skipped under any circumstances.
3. If using a CLI tool that automatically handles the GTT (like `place-intraday-amo`), verify that it succeeds.
4. If writing a custom Python script to place the order (e.g., using `broker.place_order`), your script MUST also include the `broker.place_gtt()` call in the exact same script. Do not leave it for a follow-up action.
