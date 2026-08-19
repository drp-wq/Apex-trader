"""
APEX TRADER Execution Router.
Enforces safety gates prior to routing orders to simulated paper engine.
"""
from typing import Dict, Any
from core.safety import safety_policy, SafetyViolationError
from exchanges.paper import PaperExchange
from models.domain import Order, Provenance


class ExecutionEngine:
    def __init__(self, paper_exchange: PaperExchange, safety_override=None):
        self.paper_exchange = paper_exchange
        self.safety = safety_override or safety_policy

    def submit_order(self, order: Order) -> Dict[str, Any]:
        """
        Routes an order through safety validation.
        Rejects non-paper orders and unverified states.
        """
        order_payload = {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "price": order.price,
            "quantity": order.quantity,
            "provenance": order.provenance.value if hasattr(order.provenance, "value") else str(order.provenance)
        }
        
        # Intercept and validate
        self.safety.verify_order_execution(order_payload)
        
        # Execute only in paper simulator
        return self.paper_exchange.create_order(order)
