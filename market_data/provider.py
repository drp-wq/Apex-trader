"""
Normalized Market Data Abstraction Layer for APEX TRADER.
Decouples exchange-specific formats from SMC analysis pipelines.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import time
import requests
from models.domain import Candle, Provenance
from core.safety import safety_policy, SafetyViolationError


class MarketDataProvider(ABC):
    """Abstract Base Class for all market data sources."""
    
    @abstractmethod
    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 100
    ) -> List[Candle]:
        """Fetch historical normalized candles."""
        pass

    @abstractmethod
    def get_latest_candle(
        self,
        symbol: str,
        timeframe: str = "15m"
    ) -> Optional[Candle]:
        """Fetch the most recent normalized candle."""
        pass


class InMemoryMarketDataProvider(MarketDataProvider):
    """Provider for Replay, Paper trading, and deterministic unit testing."""
    
    def __init__(self, provenance: Provenance = Provenance.PAPER):
        self.provenance = provenance
        self._candle_store: Dict[str, List[Candle]] = {}

    def push_candle(self, candle: Candle) -> None:
        """Add a candle to the in-memory series, maintaining chronological order."""
        key = f"{candle.symbol.upper()}_{candle.timeframe}"
        if key not in self._candle_store:
            self._candle_store[key] = []
        
        # Override provenance with the provider's scope
        candle.provenance = self.provenance
        self._candle_store[key].append(candle)
        self._candle_store[key].sort(key=lambda c: c.timestamp)

    def push_candles(self, candles: List[Candle]) -> None:
        for c in candles:
            self.push_candle(c)

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 100
    ) -> List[Candle]:
        key = f"{symbol.upper()}_{timeframe}"
        candles = self._candle_store.get(key, [])
        return candles[-limit:]

    def get_latest_candle(
        self,
        symbol: str,
        timeframe: str = "15m"
    ) -> Optional[Candle]:
        key = f"{symbol.upper()}_{timeframe}"
        candles = self._candle_store.get(key, [])
        return candles[-1] if candles else None

    def clear(self) -> None:
        self._candle_store.clear()


class BinancePublicRestProvider(MarketDataProvider):
    """Public read-only REST provider for Binance Futures. Requires no API keys."""
    
    def __init__(self, base_url: str = "https://fapi.binance.com"):
        safety_policy.verify_endpoint_url(base_url)
        self.base_url = base_url.rstrip("/")
        self.provenance = Provenance.REAL

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str = "15m",
        limit: int = 100
    ) -> List[Candle]:
        endpoint = f"{self.base_url}/fapi/v1/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": timeframe,
            "limit": min(limit, 1000)
        }
        
        response = requests.get(endpoint, params=params, timeout=10)
        response.raise_for_status()
        raw_klines = response.json()
        
        candles: List[Candle] = []
        for k in raw_klines:
            candles.append(Candle(
                symbol=symbol.upper(),
                timestamp=float(k[0]) / 1000.0,
                open=float(k[1]),
                high=float(k[2]),
                low=float(k[3]),
                close=float(k[4]),
                volume=float(k[5]),
                timeframe=timeframe,
                provenance=self.provenance
            ))
        return candles

    def get_latest_candle(
        self,
        symbol: str,
        timeframe: str = "15m"
    ) -> Optional[Candle]:
        candles = self.get_historical_candles(symbol, timeframe=timeframe, limit=1)
        return candles[-1] if candles else None
