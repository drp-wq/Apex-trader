from typing import Dict, Any, Optional
from exchanges.base import BaseExchange
from models.domain import Order, Position, Provenance, SignalDirection, OrderStatus
from core.safety import safety_policy

class PaperExchange(BaseExchange):
    def __init__(self, initial_balance: float = 500.0, slippage_pct: float = 0.0005, fee_pct: float = 0.0004):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.slippage_pct = slippage_pct
        self.fee_pct = fee_pct
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}

    def get_balance(self) -> float:
        return self.balance

    def create_order(self, order: Order) -> Dict[str, Any]:
        safety_policy.verify_paper_execution({"provenance": order.provenance.value})
        
        # Apply simulated slippage
        exec_price = order.price
        if order.direction == SignalDirection.BUY:
            exec_price *= (1.0 + self.slippage_pct)
        else:
            exec_price *= (1.0 - self.slippage_pct)

        fee = (exec_price * order.quantity) * self.fee_pct
        self.balance -= fee

        order.status = OrderStatus.FILLED
        self.orders[order.order_id] = order

        self.positions[order.symbol] = Position(
            symbol=order.symbol,
            direction=order.direction,
            entry_price=exec_price,
            quantity=order.quantity,
            stop_loss=order.stop_price if order.stop_price else 0.0,
            take_profit=order.take_profit_price if order.take_profit_price else 0.0,
            provenance=Provenance.PAPER
        )
        return {
            "status": "FILLED",
            "order_id": order.order_id,
            "exec_price": exec_price,
            "fee": fee
        }

    def get_positions(self) -> Dict[str, Position]:
        return self.positions

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False
