from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import time

class Provenance(str, Enum):
    REAL = "REAL"
    PAPER = "PAPER"
    REPLAY = "REPLAY"
    TESTNET = "TESTNET"

class TrendState(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    RANGING = "RANGING"

class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"

class OrderStatus(str, Enum):
    NEW = "NEW"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class Candle:
    symbol: str
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "15m"
    provenance: Provenance = Provenance.PAPER

    def __post_init__(self):
        if self.high < self.low:
            raise ValueError(f"High ({self.high}) cannot be lower than Low ({self.low})")
        if self.open < 0 or self.close < 0 or self.high < 0 or self.low < 0:
            raise ValueError("Prices must be non-negative")
        if self.timestamp < 0:
            raise ValueError("Timestamp must be non-negative")

@dataclass
class Order:
    order_id: str
    symbol: str
    direction: SignalDirection
    order_type: OrderType
    price: float
    quantity: float
    stop_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    status: OrderStatus = OrderStatus.NEW
    provenance: Provenance = Provenance.PAPER
    timestamp: float = field(default_factory=time.time)

@dataclass
class Position:
    symbol: str
    direction: SignalDirection
    entry_price: float
    quantity: float
    stop_loss: float
    take_profit: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    provenance: Provenance = Provenance.PAPER
