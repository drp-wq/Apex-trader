"""
APEX TRADER Execution Router.
Enforces safety gates and protective-order verification prior to routing orders.
"""
from typing import Dict, Any, Optional
from core.safety import safety_policy, SafetyViolationError
from execution.protection_verifier import ProtectiveOrderVerifier, ProtectiveOrderViolationError
from exchanges.paper import PaperExchange
from models.domain import Order, Provenance


class ExecutionEngine:
    def __init__(
        self,
        paper_exchange: PaperExchange,
        safety_override=None,
        protection_verifier: Optional[ProtectiveOrderVerifier] = None
    ):
        self.paper_exchange = paper_exchange
        self.safety = safety_override or safety_policy
        self.protection_verifier = protection_verifier or ProtectiveOrderVerifier()

    def submit_order(self, order: Order) -> Dict[str, Any]:
        """
        Routes an order through safety validation and protective verification.
        Rejects non-paper orders, unverified states, and missing protective orders.
        """
        order_payload = {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "price": order.price,
            "quantity": order.quantity,
            "provenance": order.provenance.value if hasattr(order.provenance, "value") else str(order.provenance)
        }
        
        # 1. Base safety check
        self.safety.verify_order_execution(order_payload)

        # 2. Protective order pre-execution verification
        current_balance = self.paper_exchange.get_balance()
        self.protection_verifier.assert_verified(order, current_balance)

        # 3. Execute in paper simulator
        return self.paper_exchange.create_order(order)
