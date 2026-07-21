import logging
import uuid
import datetime
from hsts.broker.base import BaseBroker

logger = logging.getLogger("hsts.broker.mock")

class MockBroker(BaseBroker):
    """
    Paper Trading Mock Broker Adapter for simulated execution.
    Requires no broker credentials or API keys.
    """

    def __init__(self, initial_capital=100000.0):
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.positions = {}
        self.orders = []

    def authenticate(self):
        logger.info("Mock Paper-Trading Broker authenticated successfully.")
        return True

    def get_margins(self):
        return {
            "cash": self.cash_balance,
            "total_capital": self.initial_capital,
            "used_margin": self.initial_capital - self.cash_balance
        }

    def get_positions(self):
        return self.positions

    def place_order(self, symbol, qty, transaction_type="BUY", order_type="LIMIT", price=0.0, trigger_price=0.0):
        order_id = str(uuid.uuid4())[:8]
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        total_cost = qty * price

        if transaction_type.upper() == "BUY":
            if total_cost > self.cash_balance:
                logger.error(f"Insufficient cash balance for BUY order of {symbol}. Required: INR {total_cost:.2f}, Available: INR {self.cash_balance:.2f}")
                return {"status": "FAILED", "reason": "Insufficient funds"}

            self.cash_balance -= total_cost
            if symbol in self.positions:
                prev_qty = self.positions[symbol]["qty"]
                prev_avg = self.positions[symbol]["avg_price"]
                new_qty = prev_qty + qty
                new_avg = ((prev_qty * prev_avg) + total_cost) / new_qty
                self.positions[symbol] = {"qty": new_qty, "avg_price": new_avg}
            else:
                self.positions[symbol] = {"qty": qty, "avg_price": price}

            logger.info(f"PAPER TRADE EXECUTED: Bought {qty} shares of {symbol} at INR {price:.2f}. Order ID: {order_id}")

        elif transaction_type.upper() == "SELL":
            if symbol not in self.positions or self.positions[symbol]["qty"] < qty:
                logger.error(f"Cannot SELL {symbol}: Insufficient position holdings.")
                return {"status": "FAILED", "reason": "Insufficient position"}

            self.cash_balance += total_cost
            self.positions[symbol]["qty"] -= qty
            if self.positions[symbol]["qty"] == 0:
                del self.positions[symbol]

            logger.info(f"PAPER TRADE EXECUTED: Sold {qty} shares of {symbol} at INR {price:.2f}. Order ID: {order_id}")

        order_record = {
            "order_id": order_id,
            "symbol": symbol,
            "qty": qty,
            "price": price,
            "transaction_type": transaction_type.upper(),
            "status": "COMPLETE",
            "timestamp": timestamp
        }
        self.orders.append(order_record)
        return order_record

    def cancel_order(self, order_id):
        logger.info(f"Mock order {order_id} cancelled.")
        return True
