"""
Deterministic Risk Engine for APEX TRADER.
Computes position sizing, validates R:R boundaries, and enforces risk caps.
"""
from dataclasses import dataclass
from typing import Optional
import uuid

from models.domain import SignalDirection, Order, OrderType, OrderStatus, Provenance
from analysis.setup_engine import TradeSetup


class RiskViolationError(Exception):
    pass


@dataclass(frozen=True)
class RiskCheckResult:
    is_valid: bool
    position_size: float
    notional_value: float
    risk_amount_usdt: float
    risk_pct: float
    rr_ratio: float
    rejection_reason: Optional[str] = None


class DeterministicRiskEngine:
    def __init__(
        self,
        max_account_risk_pct: float = 0.01,  # Strict 1% risk per trade
        max_leverage: int = 5,
        min_rr_ratio: float = 2.0
    ):
        self.max_account_risk_pct = max_account_risk_pct
        self.max_leverage = max_leverage
        self.min_rr_ratio = min_rr_ratio

    def evaluate_order(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        direction: SignalDirection
    ) -> RiskCheckResult:
        """Evaluates raw order parameters against risk constraints."""
        if account_balance <= 0:
            return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Account balance must be positive.")

        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Prices must be greater than zero.")

        # Directional boundary validation
        if direction == SignalDirection.BUY:
            if stop_loss >= entry_price:
                return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Long SL must be strictly below Entry.")
            if take_profit <= entry_price:
                return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Long TP must be strictly above Entry.")
        elif direction == SignalDirection.SELL:
            if stop_loss <= entry_price:
                return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Short SL must be strictly above Entry.")
            if take_profit >= entry_price:
                return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Short TP must be strictly below Entry.")
        else:
            return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Invalid direction for execution.")

        risk_per_unit = abs(entry_price - stop_loss)
        reward_per_unit = abs(take_profit - entry_price)

        if risk_per_unit == 0:
            return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Risk distance cannot be zero.")

        rr_ratio = round(reward_per_unit / risk_per_unit, 2)
        if rr_ratio < self.min_rr_ratio:
            return RiskCheckResult(
                False, 0.0, 0.0, 0.0, 0.0, rr_ratio,
                f"R:R ratio {rr_ratio} is below required minimum {self.min_rr_ratio}."
            )

        max_risk_usdt = account_balance * self.max_account_risk_pct
        position_size = max_risk_usdt / risk_per_unit

        # Max notional / leverage boundary check
        position_notional = position_size * entry_price
        max_allowed_notional = account_balance * self.max_leverage

        if position_notional > max_allowed_notional:
            position_size = max_allowed_notional / entry_price
            effective_risk = position_size * risk_per_unit
        else:
            effective_risk = max_risk_usdt

        effective_notional = position_size * entry_price
        effective_risk_pct = round((effective_risk / account_balance) * 100.0, 4)

        return RiskCheckResult(
            is_valid=True,
            position_size=round(position_size, 4),
            notional_value=round(effective_notional, 2),
            risk_amount_usdt=round(effective_risk, 2),
            risk_pct=effective_risk_pct,
            rr_ratio=rr_ratio
        )

    def evaluate_setup(
        self,
        account_balance: float,
        setup: TradeSetup
    ) -> RiskCheckResult:
        """Evaluates a TradeSetup object against account balance and risk constraints."""
        if not setup.is_valid:
            return RiskCheckResult(
                is_valid=False,
                position_size=0.0,
                notional_value=0.0,
                risk_amount_usdt=0.0,
                risk_pct=0.0,
                rr_ratio=0.0,
                rejection_reason=f"Invalid TradeSetup: {setup.rejection_reason}"
            )

        return self.evaluate_order(
            account_balance=account_balance,
            entry_price=setup.entry_price,
            stop_loss=setup.stop_loss,
            take_profit=setup.tp1,
            direction=setup.direction
        )

    def build_paper_order(
        self,
        setup: TradeSetup,
        risk_result: RiskCheckResult
    ) -> Order:
        """Constructs a normalized Order for the paper trading engine."""
        if not risk_result.is_valid:
            raise RiskViolationError(f"Cannot construct order from invalid risk result: {risk_result.rejection_reason}")

        return Order(
            order_id=f"paper-{uuid.uuid4().hex[:8]}",
            symbol=setup.symbol,
            direction=setup.direction,
            order_type=OrderType.MARKET,
            price=setup.entry_price,
            quantity=risk_result.position_size,
            stop_price=setup.stop_loss,
            take_profit_price=setup.tp1,
            status=OrderStatus.NEW,
            provenance=Provenance.PAPER,
            timestamp=setup.timestamp
        )
