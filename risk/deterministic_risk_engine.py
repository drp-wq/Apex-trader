from dataclasses import dataclass
from typing import Optional
from models.domain import SignalDirection


class RiskViolationError(Exception):
    pass


@dataclass(frozen=True)
class RiskCheckResult:
    is_valid: bool
    position_size: float
    risk_amount_usdt: float
    risk_pct: float
    rr_ratio: float
    rejection_reason: Optional[str] = None


class DeterministicRiskEngine:
    def __init__(
        self,
        max_account_risk_pct: float = 0.01,  # 1% strict risk limit
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
        if account_balance <= 0:
            return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, "Account balance must be positive.")

        if entry_price <= 0 or stop_loss <= 0 or take_profit <= 0:
            return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, "Prices must be greater than zero.")

        # Directional boundary validation
        if direction == SignalDirection.BUY:
            if stop_loss >= entry_price:
                return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, "Long SL must be strictly below Entry.")
            if take_profit <= entry_price:
                return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, "Long TP must be strictly above Entry.")
        elif direction == SignalDirection.SELL:
            if stop_loss <= entry_price:
                return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, "Short SL must be strictly above Entry.")
            if take_profit >= entry_price:
                return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, "Short TP must be strictly below Entry.")
        else:
            return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, "Invalid direction for execution.")

        risk_per_unit = abs(entry_price - stop_loss)
        reward_per_unit = abs(take_profit - entry_price)

        if risk_per_unit == 0:
            return RiskCheckResult(False, 0.0, 0.0, 0.0, 0.0, "Risk distance cannot be zero.")

        rr_ratio = round(reward_per_unit / risk_per_unit, 2)
        if rr_ratio < self.min_rr_ratio:
            return RiskCheckResult(
                False, 0.0, 0.0, 0.0, rr_ratio,
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

        effective_risk_pct = round((effective_risk / account_balance) * 100.0, 4)

        return RiskCheckResult(
            is_valid=True,
            position_size=round(position_size, 4),
            risk_amount_usdt=round(effective_risk, 2),
            risk_pct=effective_risk_pct,
            rr_ratio=rr_ratio
        )
