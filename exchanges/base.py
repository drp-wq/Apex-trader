from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from models.domain import Order, Position

class BaseExchange(ABC):
    @abstractmethod
    def get_balance(self) -> float:
        pass

    @abstractmethod
    def create_order(self, order: Order) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_positions(self) -> Dict[str, Position]:
        pass
        
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass
