"""
Data models for Smart Money Concepts (SMC) analysis.
"""
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from models.domain import TrendState


class StructureType(str, Enum):
    BOS = "BOS"
    CHOCH = "CHOCH"


class LiquidityType(str, Enum):
    BSL = "BSL"
    SSL = "SSL"


@dataclass(frozen=True)
class SwingPoint:
    index: int
    timestamp: float
    price: float
    is_high: bool


@dataclass(frozen=True)
class StructureBreak:
    index: int
    timestamp: float
    price: float
    break_type: StructureType
    direction: str  # "BULLISH" or "BEARISH"


@dataclass(frozen=True)
class MarketStructureResult:
    trend: TrendState
    swing_highs: List[SwingPoint]
    swing_lows: List[SwingPoint]
    breaks: List[StructureBreak]


@dataclass
class FVG:
    index: int
    timestamp: float
    top: float
    bottom: float
    is_bullish: bool
    mitigated: bool = False


@dataclass
class OrderBlock:
    index: int
    timestamp: float
    top: float
    bottom: float
    is_bullish: bool
    mitigated: bool = False


@dataclass
class LiquidityLevel:
    index: int
    timestamp: float
    price: float
    level_type: LiquidityType
    swept: bool = False


@dataclass(frozen=True)
class VolumeProfileResult:
    poc: float
    vah: float
    val: float
    total_volume: float
