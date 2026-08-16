---
description: Mandatory tick size rounding for all Zerodha orders (Limit, AMO, GTT)
---

# Zerodha Tick Size Rule

Whenever you are preparing to place a live order or Good-Till-Triggered (GTT) order on Zerodha, you MUST ensure that all price fields (entry price, stop loss, target, trigger limits) are rounded to the nearest `0.05` tick size before making the API call. 

Zerodha will strictly reject any order where the price is not a multiple of `0.05` (e.g., `388.72` will fail).

## Rounding Logic
Use the following mathematical logic in Python to round any calculated price to the nearest `0.05`:

```python
def round_to_tick(price):
    return round(price * 20) / 20

# Examples:
# 388.72 -> 388.70
# 486.39 -> 486.40
```

## Enforcement
Do NOT attempt to place an order or GTT with raw calculated decimal prices (like `.x1`, `.x2`, `.x8`, `.x9`). Always pre-round the variables before passing them into `broker.place_order` or `broker.place_gtt`.
