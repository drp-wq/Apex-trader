"""
Protective Order Pre-Execution Verification Barrier for APEX TRADER.
Enforces fail-closed rules: every position MUST have valid protective Stop-Loss,
Take-Profit, positive quantity, directional orientation, and risk constraints.
"""
from dataclasses import dataclass
from typing import Optional
from models.domain import Order, SignalDirection
from config.settings import get_config


class ProtectiveOrderViolationError(Exception):
    """Raised when an order fails protective safety verification."""
    pass


@dataclass(frozen=True)
class ProtectiveCheckResult:
    is_valid: bool
    symbol: str
    direction: SignalDirection
    entry_price: float
    stop_price: float
    take_profit_price: float
    quantity: float
    risk_amount: float
    risk_pct: float
    rejection_reason: Optional[str] = None


class ProtectiveOrderVerifier:
    def __init__(self, config_override=None):
        self.config = config_override or get_config()

    def verify(self, order: Order, account_balance: float) -> ProtectiveCheckResult:
        """
        Performs strict deterministic pre-execution validation.
        Fails closed on any anomaly.
        """
        if account_balance <= 0:
            return ProtectiveCheckResult(
                False, order.symbol, order.direction, order.price, 0.0, 0.0, 0.0, 0.0, 0.0,
                "Account balance must be positive."
            )

        if order.quantity <= 0:
            return ProtectiveCheckResult(
                False, order.symbol, order.direction, order.price, 0.0, 0.0, 0.0, 0.0, 0.0,
                f"Order quantity must be positive. Received: {order.quantity}"
            )

        if order.price <= 0:
            return ProtectiveCheckResult(
                False, order.symbol, order.direction, order.price, 0.0, 0.0, 0.0, 0.0, 0.0,
                f"Order price must be positive. Received: {order.price}"
            )

        # 1. Stop loss presence & placement
        if order.stop_price is None or order.stop_price <= 0:
            return ProtectiveCheckResult(
                False, order.symbol, order.direction, order.price, 0.0, 0.0, 0.0, 0.0, 0.0,
                "PROTECTIVE GATE: Missing mandatory Stop-Loss price."
            )

        # 2. Take profit presence & placement
        if order.take_profit_price is None or order.take_profit_price <= 0:
            return ProtectiveCheckResult(
                False, order.symbol, order.direction, order.price, order.stop_price, 0.0, 0.0, 0.0, 0.0,
                "PROTECTIVE GATE: Missing mandatory Take-Profit price."
            )

        # 3. Directional boundary validation
        if order.direction == SignalDirection.BUY:
            if order.stop_price >= order.price:
                return ProtectiveCheckResult(
                    False, order.symbol, order.direction, order.price, order.stop_price, order.take_profit_price,
                    order.quantity, 0.0, 0.0,
                    f"Long Stop-Loss ({order.stop_price}) must be strictly below Entry ({order.price})."
                )
            if order.take_profit_price <= order.price:
                return ProtectiveCheckResult(
                    False, order.symbol, order.direction, order.price, order.stop_price, order.take_profit_price,
                    order.quantity, 0.0, 0.0,
                    f"Long Take-Profit ({order.take_profit_price}) must be strictly above Entry ({order.price})."
                )
        elif order.direction == SignalDirection.SELL:
            if order.stop_price <= order.price:
                return ProtectiveCheckResult(
                    False, order.symbol, order.direction, order.price, order.stop_price, order.take_profit_price,
                    order.quantity, 0.0, 0.0,
                    f"Short Stop-Loss ({order.stop_price}) must be strictly above Entry ({order.price})."
                )
            if order.take_profit_price >= order.price:
                return ProtectiveCheckResult(
                    False, order.symbol, order.direction, order.price, order.stop_price, order.take_profit_price,
                    order.quantity, 0.0, 0.0,
                    f"Short Take-Profit ({order.take_profit_price}) must be strictly below Entry ({order.price})."
                )
        else:
            return ProtectiveCheckResult(
                False, order.symbol, order.direction, order.price, order.stop_price, order.take_profit_price,
                order.quantity, 0.0, 0.0,
                f"Invalid execution direction: {order.direction}"
            )

        # 4. Risk and notional limits
        risk_distance = abs(order.price - order.stop_price)
        risk_amount = round(risk_distance * order.quantity, 4)
        risk_pct = round((risk_amount / account_balance) * 100.0, 4)
        max_risk_allowed = account_balance * self.config.safety.MAX_ACCOUNT_RISK_PCT

        if risk_amount > (max_risk_allowed + 0.01):
            return ProtectiveCheckResult(
                False, order.symbol, order.direction, order.price, order.stop_price, order.take_profit_price,
                order.quantity, risk_amount, risk_pct,
                f"Risk amount ${risk_amount} exceeds maximum allowed ${max_risk_allowed:.2f} ({self.config.safety.MAX_ACCOUNT_RISK_PCT * 100}%)."
            )

        notional = order.price * order.quantity
        max_notional_allowed = account_balance * self.config.safety.MAX_LEVERAGE
        if notional > (max_notional_allowed + 0.01):
            return ProtectiveCheckResult(
                False, order.symbol, order.direction, order.price, order.stop_price, order.take_profit_price,
                order.quantity, risk_amount, risk_pct,
                f"Notional ${notional:.2f} exceeds maximum leverage limit ${max_notional_allowed:.2f} ({self.config.safety.MAX_LEVERAGE}x)."
            )

        return ProtectiveCheckResult(
            is_valid=True,
            symbol=order.symbol,
            direction=order.direction,
            entry_price=order.price,
            stop_price=order.stop_price,
            take_profit_price=order.take_profit_price,
            quantity=order.quantity,
            risk_amount=risk_amount,
            risk_pct=risk_pct
        )

    def assert_verified(self, order: Order, account_balance: float) -> None:
        """Raises ProtectiveOrderViolationError if validation fails."""
        res = self.verify(order, account_balance)
        if not res.is_valid:
            raise ProtectiveOrderViolationError(f"Protective Order Barrier Failed: {res.rejection_reason}")
