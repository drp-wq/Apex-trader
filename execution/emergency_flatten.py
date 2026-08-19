"""
Emergency Flatten Controller for APEX TRADER.
Liquidates all open paper positions immediately.
Blocks any real-money routing.
"""
import time
from typing import Dict, List, Any
from core.safety import safety_policy, SafetyViolationError
from paper.paper_engine import PaperTradingEngine, PaperTradeRecord
from models.domain import Provenance


class EmergencyFlatten:
    def __init__(self, paper_engine: PaperTradingEngine):
        self.paper_engine = paper_engine

    def flatten_all(self, current_prices: Dict[str, float]) -> List[PaperTradeRecord]:
        """
        Immediately closes all active paper positions at provided mark prices.
        Fails closed if production execution is enabled.
        """
        safety_policy.assert_production_disabled()
        
        liquidated_records: List[PaperTradeRecord] = []
        open_symbols = list(self.paper_engine.positions.keys())

        for symbol in open_symbols:
            pos = self.paper_engine.positions.get(symbol)
            if not pos:
                continue
            mark_price = current_prices.get(symbol, pos.entry_price)
            record = self.paper_engine._close_position_internal(
                symbol=symbol,
                exit_price=mark_price,
                reason="EMERGENCY_FLATTEN",
                timestamp=time.time()
            )
            liquidated_records.append(record)

        return liquidated_records

    def cancel_all_orders(self) -> int:
        """Purges any pending paper orders."""
        count = len(self.paper_engine.order_book)
        self.paper_engine.order_book.clear()
        return count
