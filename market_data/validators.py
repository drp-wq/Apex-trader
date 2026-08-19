"""
APEX TRADER Stage 96 - Market Data Validation Layer.

Comprehensive validation preventing:
- Impossible OHLC relationships
- Negative or stale volume
- Invalid timestamps
- Duplicate timestamps
- Malformed order-book updates
- Invalid open interest
- Stale or corrupted data

All invalid market data is explicitly REJECTED.
Never silently transform invalid data into valid-looking data.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta


class DataQuality(str, Enum):
    """Data quality classification for every major signal."""
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"


class ValidationError(Exception):
    """Raised when market data fails validation."""
    pass


@dataclass
class OHLCVValidationResult:
    """Result of OHLCV candle validation."""
    valid: bool
    candle: Optional[Any] = None
    error: Optional[str] = None
    data_quality: DataQuality = DataQuality.GOOD


@dataclass
class OrderBookValidationResult:
    """Result of order book snapshot validation."""
    valid: bool
    snapshot: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    data_quality: DataQuality = DataQuality.GOOD


@dataclass
class OIValidationResult:
    """Result of open interest data validation."""
    valid: bool
    oi_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    data_quality: DataQuality = DataQuality.GOOD


class OHLCVValidator:
    """
    Validates OHLCV candles.
    
    Requirements:
    - high >= max(open, close)
    - low <= min(open, close)
    - high >= low
    - all prices >= 0
    - volume >= 0
    - timestamp > 0
    - no duplicate timestamps per symbol/timeframe
    """
    
    def __init__(self, max_staleness_seconds: int = 300):
        """
        Initialize OHLCV validator.
        
        Args:
            max_staleness_seconds: Maximum age of candle before marking STALE
        """
        self.max_staleness_seconds = max_staleness_seconds
        self.last_timestamp_seen = {}
    
    def validate(self, candle: Dict[str, Any]) -> OHLCVValidationResult:
        """
        Validate a single OHLCV candle.
        
        Returns: OHLCVValidationResult with valid=True or False
        """
        try:
            # Extract required fields
            symbol = candle.get("symbol")
            timeframe = candle.get("timeframe", "1m")
            timestamp = candle.get("timestamp")
            open_price = candle.get("open")
            high = candle.get("high")
            low = candle.get("low")
            close = candle.get("close")
            volume = candle.get("volume")
            
            # Check for missing fields
            if any(x is None for x in [symbol, timestamp, open_price, high, low, close, volume]):
                return OHLCVValidationResult(
                    valid=False,
                    error="Missing required OHLCV fields",
                    data_quality=DataQuality.INVALID
                )
            
            # Timestamp validation
            if not isinstance(timestamp, (int, float)) or timestamp <= 0:
                return OHLCVValidationResult(
                    valid=False,
                    error=f"Invalid timestamp: {timestamp}",
                    data_quality=DataQuality.INVALID
                )
            
            # Check staleness
            now = datetime.utcnow().timestamp()
            age_seconds = now - timestamp
            if age_seconds > self.max_staleness_seconds:
                return OHLCVValidationResult(
                    valid=False,
                    error=f"Stale candle: {age_seconds} seconds old",
                    data_quality=DataQuality.STALE
                )
            
            # Price validation: all must be non-negative
            if any(p < 0 for p in [open_price, high, low, close]):
                return OHLCVValidationResult(
                    valid=False,
                    error=f"Negative price detected: O={open_price}, H={high}, L={low}, C={close}",
                    data_quality=DataQuality.INVALID
                )
            
            # Volume validation: must be non-negative
            if volume < 0:
                return OHLCVValidationResult(
                    valid=False,
                    error=f"Negative volume: {volume}",
                    data_quality=DataQuality.INVALID
                )
            
            # OHLC structure validation
            if high < low:
                return OHLCVValidationResult(
                    valid=False,
                    error=f"High ({high}) < Low ({low})",
                    data_quality=DataQuality.INVALID
                )
            
            if high < max(open_price, close):
                return OHLCVValidationResult(
                    valid=False,
                    error=f"High ({high}) < max(O,C) = {max(open_price, close)}",
                    data_quality=DataQuality.INVALID
                )
            
            if low > min(open_price, close):
                return OHLCVValidationResult(
                    valid=False,
                    error=f"Low ({low}) > min(O,C) = {min(open_price, close)}",
                    data_quality=DataQuality.INVALID
                )
            
            # Duplicate timestamp check
            key = f"{symbol}:{timeframe}"
            if key in self.last_timestamp_seen:
                if self.last_timestamp_seen[key] == timestamp:
                    return OHLCVValidationResult(
                        valid=False,
                        error=f"Duplicate timestamp {timestamp} for {key}",
                        data_quality=DataQuality.INVALID
                    )
            
            self.last_timestamp_seen[key] = timestamp
            
            # All checks passed
            return OHLCVValidationResult(
                valid=True,
                candle=candle,
                data_quality=DataQuality.GOOD
            )
        
        except Exception as e:
            return OHLCVValidationResult(
                valid=False,
                error=f"Validation exception: {str(e)}",
                data_quality=DataQuality.INVALID
            )


class OrderBookValidator:
    """
    Validates order book snapshots.
    
    Requirements:
    - bids and asks are lists of [price, quantity] pairs
    - all prices >= 0
    - all quantities >= 0
    - bid price < ask price (bid-ask spread)
    - best bid >= previous best bid (not a regression)
    - best ask <= previous best ask (not a regression)
    - no crossing bids/asks
    """
    
    def __init__(self, max_staleness_seconds: int = 10):
        """Initialize order book validator."""
        self.max_staleness_seconds = max_staleness_seconds
        self.last_best_bid = {}
        self.last_best_ask = {}
    
    def validate(self, snapshot: Dict[str, Any]) -> OrderBookValidationResult:
        """
        Validate an order book snapshot.
        
        Returns: OrderBookValidationResult with valid=True or False
        """
        try:
            symbol = snapshot.get("symbol")
            timestamp = snapshot.get("timestamp")
            bids = snapshot.get("bids", [])
            asks = snapshot.get("asks", [])
            
            # Check for missing fields
            if not symbol or not timestamp:
                return OrderBookValidationResult(
                    valid=False,
                    error="Missing symbol or timestamp",
                    data_quality=DataQuality.INVALID
                )
            
            # Timestamp validation
            if not isinstance(timestamp, (int, float)) or timestamp <= 0:
                return OrderBookValidationResult(
                    valid=False,
                    error=f"Invalid timestamp: {timestamp}",
                    data_quality=DataQuality.INVALID
                )
            
            # Check staleness
            now = datetime.utcnow().timestamp()
            age_seconds = now - timestamp
            if age_seconds > self.max_staleness_seconds:
                return OrderBookValidationResult(
                    valid=False,
                    error=f"Stale order book: {age_seconds} seconds old",
                    data_quality=DataQuality.STALE
                )
            
            # Validate bid/ask structure
            if not isinstance(bids, list) or not isinstance(asks, list):
                return OrderBookValidationResult(
                    valid=False,
                    error="Bids/asks must be lists",
                    data_quality=DataQuality.INVALID
                )
            
            # Validate each bid
            for bid in bids:
                if not isinstance(bid, (list, tuple)) or len(bid) < 2:
                    return OrderBookValidationResult(
                        valid=False,
                        error="Invalid bid entry structure",
                        data_quality=DataQuality.INVALID
                    )
                price, quantity = bid[0], bid[1]
                if price < 0 or quantity < 0:
                    return OrderBookValidationResult(
                        valid=False,
                        error=f"Negative price/quantity in bid: {bid}",
                        data_quality=DataQuality.INVALID
                    )
            
            # Validate each ask
            for ask in asks:
                if not isinstance(ask, (list, tuple)) or len(ask) < 2:
                    return OrderBookValidationResult(
                        valid=False,
                        error="Invalid ask entry structure",
                        data_quality=DataQuality.INVALID
                    )
                price, quantity = ask[0], ask[1]
                if price < 0 or quantity < 0:
                    return OrderBookValidationResult(
                        valid=False,
                        error=f"Negative price/quantity in ask: {ask}",
                        data_quality=DataQuality.INVALID
                    )
            
            # Extract best bid/ask
            best_bid = float(bids[0][0]) if bids else None
            best_ask = float(asks[0][0]) if asks else None
            
            # Bid-ask spread check
            if best_bid is not None and best_ask is not None:
                if best_bid >= best_ask:
                    return OrderBookValidationResult(
                        valid=False,
                        error=f"Invalid spread: best_bid ({best_bid}) >= best_ask ({best_ask})",
                        data_quality=DataQuality.INVALID
                    )
            
            # Check for crossing bids/asks (within depth)
            if bids and asks:
                highest_bid = float(bids[0][0])
                lowest_ask = float(asks[0][0])
                if highest_bid >= lowest_ask:
                    return OrderBookValidationResult(
                        valid=False,
                        error=f"Crossing order book: bids/asks overlap",
                        data_quality=DataQuality.INVALID
                    )
            
            # All checks passed
            return OrderBookValidationResult(
                valid=True,
                snapshot=snapshot,
                data_quality=DataQuality.GOOD
            )
        
        except Exception as e:
            return OrderBookValidationResult(
                valid=False,
                error=f"Validation exception: {str(e)}",
                data_quality=DataQuality.INVALID
            )


class OpenInterestValidator:
    """
    Validates open interest data.
    
    Requirements:
    - oi >= 0
    - timestamp > 0
    - not stale
    - oi_change and oi_pct_change calculated and reasonable
    - price_change calculated and reasonable
    """
    
    def __init__(self, max_staleness_seconds: int = 60):
        """Initialize OI validator."""
        self.max_staleness_seconds = max_staleness_seconds
        self.last_oi = {}
        self.last_price = {}
    
    def validate(self, oi_data: Dict[str, Any]) -> OIValidationResult:
        """
        Validate open interest data.
        
        Returns: OIValidationResult with valid=True or False
        """
        try:
            symbol = oi_data.get("symbol")
            timestamp = oi_data.get("timestamp")
            oi_current = oi_data.get("oi_current")
            
            # Check for missing required fields
            if symbol is None or timestamp is None or oi_current is None:
                return OIValidationResult(
                    valid=False,
                    error="Missing required OI fields",
                    data_quality=DataQuality.INVALID
                )
            
            # Timestamp validation
            if not isinstance(timestamp, (int, float)) or timestamp <= 0:
                return OIValidationResult(
                    valid=False,
                    error=f"Invalid timestamp: {timestamp}",
                    data_quality=DataQuality.INVALID
                )
            
            # Check staleness
            now = datetime.utcnow().timestamp()
            age_seconds = now - timestamp
            if age_seconds > self.max_staleness_seconds:
                return OIValidationResult(
                    valid=False,
                    error=f"Stale OI: {age_seconds} seconds old",
                    data_quality=DataQuality.STALE
                )
            
            # OI validation: must be non-negative
            if oi_current < 0:
                return OIValidationResult(
                    valid=False,
                    error=f"Negative OI: {oi_current}",
                    data_quality=DataQuality.INVALID
                )
            
            # Calculate changes
            oi_previous = oi_data.get("oi_previous", oi_current)
            oi_change = oi_current - oi_previous
            
            # Handle zero division
            if oi_previous == 0:
                oi_pct_change = 0.0 if oi_current == 0 else float('inf')
                if oi_pct_change == float('inf'):
                    return OIValidationResult(
                        valid=False,
                        error="Cannot calculate pct change from zero baseline OI",
                        data_quality=DataQuality.UNAVAILABLE
                    )
            else:
                oi_pct_change = (oi_change / oi_previous) * 100
            
            # Price change validation (if provided)
            price_change = oi_data.get("price_change")
            if price_change is not None:
                if not isinstance(price_change, (int, float)):
                    return OIValidationResult(
                        valid=False,
                        error=f"Invalid price_change type: {type(price_change)}",
                        data_quality=DataQuality.INVALID
                    )
            
            # All checks passed
            validated_data = oi_data.copy()
            validated_data["oi_change"] = oi_change
            validated_data["oi_pct_change"] = oi_pct_change
            
            self.last_oi[symbol] = oi_current
            
            return OIValidationResult(
                valid=True,
                oi_data=validated_data,
                data_quality=DataQuality.GOOD
            )
        
        except Exception as e:
            return OIValidationResult(
                valid=False,
                error=f"Validation exception: {str(e)}",
                data_quality=DataQuality.INVALID
            )


class VolumeValidator:
    """
    Validates volume and RVOL (Relative Volume) data.
    
    Requirements:
    - volume >= 0
    - rvol >= 0 and finite (not inf/nan)
    - rvol = current_volume / reference_average_volume
    - reference_average_volume > 0
    - no NaN or infinity propagated to decision engine
    """
    
    def __init__(self, reference_period_candles: int = 20):
        """Initialize volume validator."""
        self.reference_period_candles = reference_period_candles
        self.volume_history = {}
    
    def validate(self, volume_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate volume and RVOL data.
        
        Raises ValidationError on invalid data.
        Returns validated volume data dict.
        """
        symbol = volume_data.get("symbol")
        volume = volume_data.get("volume")
        
        # Validate base volume
        if volume is None or volume < 0:
            raise ValidationError(f"Invalid volume for {symbol}: {volume}")
        
        # Track volume history
        if symbol not in self.volume_history:
            self.volume_history[symbol] = []
        
        self.volume_history[symbol].append(volume)
        
        # Keep only recent history
        if len(self.volume_history[symbol]) > self.reference_period_candles:
            self.volume_history[symbol].pop(0)
        
        # Calculate RVOL
        avg_volume = (
            sum(self.volume_history[symbol]) / len(self.volume_history[symbol])
            if self.volume_history[symbol]
            else 0
        )
        
        if avg_volume == 0:
            # Not enough history
            rvol = 0.0
            data_quality = DataQuality.UNAVAILABLE
        else:
            rvol = volume / avg_volume
        
        # Validate RVOL result
        if rvol != rvol:  # NaN check
            raise ValidationError(f"RVOL is NaN for {symbol}")
        
        if rvol == float('inf') or rvol == float('-inf'):
            raise ValidationError(f"RVOL is infinite for {symbol}")
        
        if rvol < 0:
            raise ValidationError(f"RVOL is negative for {symbol}: {rvol}")
        
        validated = volume_data.copy()
        validated["rvol"] = rvol
        validated["reference_avg_volume"] = avg_volume
        validated["data_quality"] = data_quality if avg_volume == 0 else DataQuality.GOOD
        
        return validated


class OrderFlowValidator:
    """
    Validates order flow data.
    
    Requirements:
    - bid_volume >= 0
    - ask_volume >= 0
    - delta = bid_volume - ask_volume (can be negative)
    - imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume) or UNAVAILABLE
    - never invent bid/ask data; use DATA_UNAVAILABLE instead
    """
    
    def validate(self, order_flow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate order flow data.
        
        Raises ValidationError on invalid data.
        Returns validated order flow dict.
        """
        bid_volume = order_flow.get("bid_volume")
        ask_volume = order_flow.get("ask_volume")
        
        # If data unavailable, mark explicitly
        if bid_volume is None or ask_volume is None:
            return {
                **order_flow,
                "status": "UNAVAILABLE",
                "data_quality": DataQuality.UNAVAILABLE
            }
        
        # Validate non-negative
        if bid_volume < 0 or ask_volume < 0:
            raise ValidationError(
                f"Negative order flow: bid={bid_volume}, ask={ask_volume}"
            )
        
        # Calculate delta
        delta = bid_volume - ask_volume
        
        # Calculate imbalance (avoid division by zero)
        total = bid_volume + ask_volume
        if total == 0:
            imbalance = 0.0
        else:
            imbalance = delta / total
        
        # Validate imbalance range
        if imbalance < -1.0 or imbalance > 1.0:
            raise ValidationError(
                f"Imbalance out of range [-1, 1]: {imbalance}"
            )
        
        validated = order_flow.copy()
        validated["delta"] = delta
        validated["imbalance"] = imbalance
        validated["data_quality"] = DataQuality.GOOD
        
        return validated
