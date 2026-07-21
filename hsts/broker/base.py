from abc import ABC, abstractmethod
import logging

logger = logging.getLogger("hsts.broker")

class BaseBroker(ABC):
    """
    Abstract Base Class for all Broker Adapters (Mock, Zerodha Free, Zerodha Official).
    """

    @abstractmethod
    def authenticate(self):
        """Authenticate with the broker."""
        pass

    @abstractmethod
    def get_margins(self):
        """Get available trading margins/balance."""
        pass

    @abstractmethod
    def get_positions(self):
        """Get current open positions."""
        pass

    @abstractmethod
    def place_order(self, symbol, qty, transaction_type="BUY", order_type="LIMIT", price=0.0, trigger_price=0.0):
        """Place a new trade order."""
        pass

    @abstractmethod
    def cancel_order(self, order_id):
        """Cancel an existing open order."""
        pass
