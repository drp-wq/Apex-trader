"""
Full-featured Paper Trading Execution Engine for APEX TRADER.
Simulates market/limit order matching, SL/TP triggers, trailing stops, fees, and PnL.
Enforces strict PAPER provenance and fail-closed safety.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time
import uuid

from models.domain import (
    Candle,
    Order,
    Position,
    SignalDirection,
    OrderType,
    OrderStatus,
    Provenance,
)
from core.safety import safety_policy, SafetyViolationError


@dataclass
class PaperTradeRecord:
    trade_id: str
    symbol: str
    direction: SignalDirection
    entry_price: float
    exit_price: float
    quantity: float
    realized_pnl: float
    fees_paid: float
    entry_time: float
    exit_time: float
    exit_reason: str  # "STOP_LOSS", "TAKE_PROFIT", "MANUAL", "EMERGENCY_FLATTEN"
    provenance: Provenance = Provenance.PAPER


@dataclass
class ActivePaperPosition:
    symbol: str
    direction: SignalDirection
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    tp2: Optional[float] = None
    tp3: Optional[float] = None
    trailing_stop_distance: Optional[float] = None
    highest_price: float = 0.0
    lowest_price: float = float("inf")
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_fees: float = 0.0
    opened_at: float = field(default_factory=time.time)
    provenance: Provenance = Provenance.PAPER


class PaperTradingEngine:
    def __init__(
        self,
        initial_balance: float = 500.0,
        slippage_pct: float = 0.0005,  # 0.05% slippage
        fee_pct: float = 0.0004         # 0.04% taker fee
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct

        self.positions: Dict[str, ActivePaperPosition] = {}
        self.trade_history: List[PaperTradeRecord] = []
        self.order_book: Dict[str, Order] = {}

    def get_balance(self) -> float:
        return self.balance

    def get_positions(self) -> Dict[str, ActivePaperPosition]:
        return self.positions

    def create_order(self, order: Order) -> Dict[str, Any]:
        return self.execute_order(order)

    def execute_order(
        self,
        order: Order,
        tp2: Optional[float] = None,
        tp3: Optional[float] = None,
        trailing_stop_distance: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes a paper order, applying simulated slippage, commission fees, and safety checks.
        """
        # Safety validation
        safety_policy.verify_paper_execution({"provenance": order.provenance.value if hasattr(order.provenance, "value") else str(order.provenance)})

        # Apply slippage to entry
        exec_price = order.price
        if order.direction == SignalDirection.BUY:
            exec_price *= (1.0 + self.slippage_pct)
        else:
            exec_price *= (1.0 - self.slippage_pct)
        exec_price = round(exec_price, 4)

        entry_fee = round((exec_price * order.quantity) * self.fee_pct, 4)
        self.balance -= entry_fee

        order.status = OrderStatus.FILLED
        self.order_book[order.order_id] = order

        pos = ActivePaperPosition(
            symbol=order.symbol,
            direction=order.direction,
            entry_price=exec_price,
            quantity=order.quantity,
            stop_loss=order.stop_price if order.stop_price else 0.0,
            take_profit=order.take_profit_price if order.take_profit_price else 0.0,
            tp2=tp2,
            tp3=tp3,
            trailing_stop_distance=trailing_stop_distance,
            highest_price=exec_price,
            lowest_price=exec_price,
            total_fees=entry_fee,
            opened_at=order.timestamp,
            provenance=Provenance.PAPER
        )
        self.positions[order.symbol] = pos

        return {
            "status": "FILLED",
            "order_id": order.order_id,
            "symbol": order.symbol,
            "exec_price": exec_price,
            "quantity": order.quantity,
            "fee": entry_fee,
            "provenance": Provenance.PAPER.value
        }

    def on_price_update(self, candle: Candle) -> List[PaperTradeRecord]:
        """
        Evaluates incoming candle against open positions.
        Triggers Stop Loss, Take Profit, and updates Trailing Stops.
        """
        closed_records: List[PaperTradeRecord] = []
        symbol = candle.symbol

        if symbol not in self.positions:
            return closed_records

        pos = self.positions[symbol]
        pos.highest_price = max(pos.highest_price, candle.high)
        pos.lowest_price = min(pos.lowest_price, candle.low)

        # Mark-to-Market Unrealized PnL
        if pos.direction == SignalDirection.BUY:
            pos.unrealized_pnl = round((candle.close - pos.entry_price) * pos.quantity, 4)
        else:
            pos.unrealized_pnl = round((pos.entry_price - candle.close) * pos.quantity, 4)

        # Check triggers against current stop/target levels
        if pos.direction == SignalDirection.BUY:
            if pos.stop_loss > 0 and candle.low <= pos.stop_loss:
                closed = self._close_position_internal(symbol, pos.stop_loss, "STOP_LOSS", candle.timestamp)
                closed_records.append(closed)
                return closed_records
            elif pos.take_profit > 0 and candle.high >= pos.take_profit:
                closed = self._close_position_internal(symbol, pos.take_profit, "TAKE_PROFIT", candle.timestamp)
                closed_records.append(closed)
                return closed_records

        elif pos.direction == SignalDirection.SELL:
            if pos.stop_loss > 0 and candle.high >= pos.stop_loss:
                closed = self._close_position_internal(symbol, pos.stop_loss, "STOP_LOSS", candle.timestamp)
                closed_records.append(closed)
                return closed_records
            elif pos.take_profit > 0 and candle.low <= pos.take_profit:
                closed = self._close_position_internal(symbol, pos.take_profit, "TAKE_PROFIT", candle.timestamp)
                closed_records.append(closed)
                return closed_records

        # Dynamic Trailing Stop update for subsequent bars
        if pos.trailing_stop_distance and pos.trailing_stop_distance > 0:
            if pos.direction == SignalDirection.BUY:
                new_sl = round(pos.highest_price - pos.trailing_stop_distance, 4)
                if new_sl > pos.stop_loss:
                    pos.stop_loss = new_sl
            elif pos.direction == SignalDirection.SELL:
                new_sl = round(pos.lowest_price + pos.trailing_stop_distance, 4)
                if new_sl < pos.stop_loss or pos.stop_loss == 0.0:
                    pos.stop_loss = new_sl

        return closed_records

    def _close_position_internal(
        self,
        symbol: str,
        exit_price: float,
        reason: str,
        timestamp: float
    ) -> PaperTradeRecord:
        """Internal position liquidation and trade record finalization."""
        pos = self.positions.pop(symbol)

        # Apply slippage on exit
        if pos.direction == SignalDirection.BUY:
            exec_exit = round(exit_price * (1.0 - self.slippage_pct), 4)
            gross_pnl = (exec_exit - pos.entry_price) * pos.quantity
        else:
            exec_exit = round(exit_price * (1.0 + self.slippage_pct), 4)
            gross_pnl = (pos.entry_price - exec_exit) * pos.quantity

        exit_fee = round((exec_exit * pos.quantity) * self.fee_pct, 4)
        total_fees = round(pos.total_fees + exit_fee, 4)
        net_pnl = round(gross_pnl - exit_fee, 4)

        self.balance = round(self.balance + gross_pnl - exit_fee, 4)

        record = PaperTradeRecord(
            trade_id=f"trade-{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            direction=pos.direction,
            entry_price=pos.entry_price,
            exit_price=exec_exit,
            quantity=pos.quantity,
            realized_pnl=net_pnl,
            fees_paid=total_fees,
            entry_time=pos.opened_at,
            exit_time=timestamp,
            exit_reason=reason,
            provenance=Provenance.PAPER
        )
        self.trade_history.append(record)
        return record

    def close_position_manually(self, symbol: str, current_price: float) -> Optional[PaperTradeRecord]:
        """Manually closes an open paper position at current market price."""
        if symbol in self.positions:
            return self._close_position_internal(symbol, current_price, "MANUAL", time.time())
        return None

    def get_account_summary(self) -> Dict[str, Any]:
        """Returns the paper portfolio equity, unrealized PnL, and balance metrics."""
        unrealized = sum(p.unrealized_pnl for p in self.positions.values())
        equity = round(self.balance + unrealized, 4)
        return {
            "balance": round(self.balance, 4),
            "equity": equity,
            "unrealized_pnl": round(unrealized, 4),
            "open_positions_count": len(self.positions),
            "total_trades_count": len(self.trade_history),
            "provenance": Provenance.PAPER.value
        }
