import logging

logger = logging.getLogger("hsts.risk")

class RiskManagementEngine:
    def __init__(self, max_portfolio_risk_per_trade=0.01, min_risk_reward_ratio=2.0):
        """
        Default:
        - Risk 1% of total capital per trade.
        - Require minimum 1:2 Risk-to-Reward ratio.
        """
        self.max_portfolio_risk_per_trade = max_portfolio_risk_per_trade
        self.min_risk_reward_ratio = min_risk_reward_ratio

    def calculate_position_size(self, total_capital, entry_price, stop_loss_price):
        """
        Calculate stock quantity and trade risk parameters.
        """
        import math
        
        if math.isnan(entry_price) or math.isnan(stop_loss_price):
            logger.error("Entry price or stop loss is NaN.")
            return None

        if entry_price <= stop_loss_price:
            logger.error("Entry price must be greater than stop loss price for a long trade.")
            return None

        # Max capital amount we can lose in this trade
        max_loss_amount = total_capital * self.max_portfolio_risk_per_trade
        
        # Risk per share
        risk_per_share = entry_price - stop_loss_price
        if math.isnan(risk_per_share) or risk_per_share <= 0:
            logger.error("Invalid risk per share calculated.")
            return None

        # Quantity to purchase
        quantity = int(max_loss_amount // risk_per_share)
        
        # Capital allocation for this position
        total_investment = quantity * entry_price

        # Safeguard: Never allocate more than 20% of total capital to a single stock
        max_allocation = total_capital * 0.20
        if total_investment > max_allocation:
            quantity = int(max_allocation // entry_price)
            total_investment = quantity * entry_price
            logger.info(f"Position size capped to 20% max allocation limit. New quantity: {quantity}")

        return {
            "quantity": quantity,
            "total_investment": total_investment,
            "pct_of_portfolio": total_investment / total_capital,
            "max_loss_amount": quantity * risk_per_share
        }

    def validate_trade(self, entry_price, stop_loss_price, target_price):
        """
        Check if the trade setup meets minimum Risk-to-Reward ratio.
        """
        risk = entry_price - stop_loss_price
        reward = target_price - entry_price

        if risk <= 0:
            return False, "Invalid stop loss level."

        rr_ratio = reward / risk
        if rr_ratio < self.min_risk_reward_ratio:
            return False, f"Risk-to-Reward ratio ({rr_ratio:.2f}) is below minimum target of {self.min_risk_reward_ratio}."

        return True, "Trade configuration verified."
