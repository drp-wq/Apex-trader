"""
Tests for market data validation layer.

Comprehensive test coverage for:
- OHLCV validation
- Order book validation
- Open interest validation
- Volume and RVOL validation
- Order flow validation
- Data quality classification
"""

import pytest
from market_data.validators import (
    OHLCVValidator,
    OrderBookValidator,
    OpenInterestValidator,
    VolumeValidator,
    OrderFlowValidator,
    DataQuality,
    ValidationError,
    OHLCVValidationResult,
)
import time


class TestOHLCVValidator:
    """Test OHLCV candle validation."""
    
    def test_valid_candle(self):
        """Test validation of a valid candle."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": 50000.0,
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": 100.5,
            "timeframe": "1m"
        }
        result = validator.validate(candle)
        assert result.valid is True
        assert result.data_quality == DataQuality.GOOD
        assert result.candle == candle
    
    def test_missing_fields(self):
        """Test rejection of candle with missing fields."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": 50000.0,
            # missing high, low, close, volume
        }
        result = validator.validate(candle)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
        assert "missing" in result.error.lower()
    
    def test_negative_price(self):
        """Test rejection of negative prices."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": -50000.0,  # negative
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": 100.5,
        }
        result = validator.validate(candle)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
    
    def test_negative_volume(self):
        """Test rejection of negative volume."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": 50000.0,
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": -100.5,  # negative
        }
        result = validator.validate(candle)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
    
    def test_high_less_than_low(self):
        """Test rejection of high < low."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": 50000.0,
            "high": 49500.0,  # less than low
            "low": 51000.0,
            "close": 50500.0,
            "volume": 100.5,
        }
        result = validator.validate(candle)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
        assert "high" in result.error.lower() and "low" in result.error.lower()
    
    def test_high_less_than_open_close(self):
        """Test rejection of high < max(open, close)."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": 50000.0,
            "high": 49999.0,  # less than open
            "low": 49500.0,
            "close": 50500.0,
            "volume": 100.5,
        }
        result = validator.validate(candle)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
    
    def test_low_greater_than_open_close(self):
        """Test rejection of low > min(open, close)."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": 50000.0,
            "high": 51000.0,
            "low": 50001.0,  # greater than open
            "close": 50500.0,
            "volume": 100.5,
        }
        result = validator.validate(candle)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
    
    def test_stale_candle(self):
        """Test detection of stale candles."""
        validator = OHLCVValidator(max_staleness_seconds=60)
        old_timestamp = time.time() - 120  # 2 minutes old
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": old_timestamp,
            "open": 50000.0,
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": 100.5,
        }
        result = validator.validate(candle)
        assert result.valid is False
        assert result.data_quality == DataQuality.STALE
        assert "stale" in result.error.lower()
    
    def test_duplicate_timestamp(self):
        """Test detection of duplicate timestamps."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": 1000000.0,
            "open": 50000.0,
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": 100.5,
        }
        # First candle accepted
        result1 = validator.validate(candle)
        assert result1.valid is True
        
        # Duplicate timestamp rejected
        result2 = validator.validate(candle)
        assert result2.valid is False
        assert result2.data_quality == DataQuality.INVALID
        assert "duplicate" in result2.error.lower()


class TestOrderBookValidator:
    """Test order book snapshot validation."""
    
    def test_valid_order_book(self):
        """Test validation of a valid order book."""
        validator = OrderBookValidator()
        snapshot = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "bids": [[50000.0, 10.0], [49999.0, 20.0]],
            "asks": [[50001.0, 15.0], [50002.0, 25.0]]
        }
        result = validator.validate(snapshot)
        assert result.valid is True
        assert result.data_quality == DataQuality.GOOD
    
    def test_missing_symbol(self):
        """Test rejection of missing symbol."""
        validator = OrderBookValidator()
        snapshot = {
            "timestamp": time.time(),
            "bids": [[50000.0, 10.0]],
            "asks": [[50001.0, 15.0]]
        }
        result = validator.validate(snapshot)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
    
    def test_negative_bid_price(self):
        """Test rejection of negative bid price."""
        validator = OrderBookValidator()
        snapshot = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "bids": [[-50000.0, 10.0]],  # negative price
            "asks": [[50001.0, 15.0]]
        }
        result = validator.validate(snapshot)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
    
    def test_negative_ask_quantity(self):
        """Test rejection of negative ask quantity."""
        validator = OrderBookValidator()
        snapshot = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "bids": [[50000.0, 10.0]],
            "asks": [[50001.0, -15.0]]  # negative quantity
        }
        result = validator.validate(snapshot)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
    
    def test_bid_ask_crossing(self):
        """Test detection of bid-ask crossing (invalid)."""
        validator = OrderBookValidator()
        snapshot = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "bids": [[50001.0, 10.0]],  # bid >= ask (invalid)
            "asks": [[50000.0, 15.0]]
        }
        result = validator.validate(snapshot)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
        assert "spread" in result.error.lower() or "crossing" in result.error.lower()
    
    def test_stale_order_book(self):
        """Test detection of stale order book."""
        validator = OrderBookValidator(max_staleness_seconds=30)
        old_timestamp = time.time() - 60  # 1 minute old
        snapshot = {
            "symbol": "BTCUSDT",
            "timestamp": old_timestamp,
            "bids": [[50000.0, 10.0]],
            "asks": [[50001.0, 15.0]]
        }
        result = validator.validate(snapshot)
        assert result.valid is False
        assert result.data_quality == DataQuality.STALE


class TestOpenInterestValidator:
    """Test open interest validation."""
    
    def test_valid_oi_data(self):
        """Test validation of valid OI data."""
        validator = OpenInterestValidator()
        oi_data = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "oi_current": 1000000.0,
            "oi_previous": 950000.0
        }
        result = validator.validate(oi_data)
        assert result.valid is True
        assert result.data_quality == DataQuality.GOOD
        assert result.oi_data["oi_change"] == 50000.0
        assert result.oi_data["oi_pct_change"] == pytest.approx(5.263, rel=0.01)
    
    def test_negative_oi(self):
        """Test rejection of negative OI."""
        validator = OpenInterestValidator()
        oi_data = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "oi_current": -1000000.0,  # negative
            "oi_previous": 950000.0
        }
        result = validator.validate(oi_data)
        assert result.valid is False
        assert result.data_quality == DataQuality.INVALID
    
    def test_zero_baseline_oi(self):
        """Test handling of zero baseline OI (division by zero)."""
        validator = OpenInterestValidator()
        oi_data = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "oi_current": 1000000.0,
            "oi_previous": 0.0  # zero baseline
        }
        result = validator.validate(oi_data)
        # Should mark as unavailable rather than returning infinity
        assert result.valid is False or result.data_quality == DataQuality.UNAVAILABLE
    
    def test_stale_oi(self):
        """Test detection of stale OI."""
        validator = OpenInterestValidator(max_staleness_seconds=60)
        old_timestamp = time.time() - 120
        oi_data = {
            "symbol": "BTCUSDT",
            "timestamp": old_timestamp,
            "oi_current": 1000000.0,
            "oi_previous": 950000.0
        }
        result = validator.validate(oi_data)
        assert result.valid is False
        assert result.data_quality == DataQuality.STALE


class TestVolumeValidator:
    """Test volume and RVOL validation."""
    
    def test_valid_volume(self):
        """Test validation of valid volume."""
        validator = VolumeValidator(reference_period_candles=2)
        volume_data = {"symbol": "BTCUSDT", "volume": 100.0}
        
        result = validator.validate(volume_data)
        assert "rvol" in result
        assert result["volume"] == 100.0
        assert result["data_quality"] == DataQuality.UNAVAILABLE  # not enough history
    
    def test_negative_volume_rejected(self):
        """Test rejection of negative volume."""
        validator = VolumeValidator()
        volume_data = {"symbol": "BTCUSDT", "volume": -50.0}
        
        with pytest.raises(ValidationError, match="invalid volume"):
            validator.validate(volume_data)
    
    def test_rvol_calculation(self):
        """Test RVOL calculation with sufficient history."""
        validator = VolumeValidator(reference_period_candles=3)
        
        # Add 3 volumes to build history
        v1 = {"symbol": "BTCUSDT", "volume": 100.0}
        v2 = {"symbol": "BTCUSDT", "volume": 100.0}
        v3 = {"symbol": "BTCUSDT", "volume": 100.0}
        
        validator.validate(v1)
        validator.validate(v2)
        result = validator.validate(v3)
        
        # Average is 100, current is 100, so RVOL should be 1.0
        assert result["rvol"] == 1.0
        assert result["data_quality"] == DataQuality.GOOD
    
    def test_rvol_expansion(self):
        """Test RVOL > 1 (volume expansion)."""
        validator = VolumeValidator(reference_period_candles=2)
        
        v1 = {"symbol": "BTCUSDT", "volume": 100.0}
        v2 = {"symbol": "BTCUSDT", "volume": 200.0}  # higher
        
        validator.validate(v1)
        result = validator.validate(v2)
        
        avg = 150.0
        rvol = 200.0 / 150.0
        assert result["rvol"] == pytest.approx(rvol, rel=0.01)
        assert result["rvol"] > 1.0


class TestOrderFlowValidator:
    """Test order flow validation."""
    
    def test_valid_order_flow(self):
        """Test validation of valid order flow."""
        validator = OrderFlowValidator()
        order_flow = {
            "symbol": "BTCUSDT",
            "bid_volume": 100.0,
            "ask_volume": 80.0
        }
        result = validator.validate(order_flow)
        assert result["delta"] == 20.0
        assert result["imbalance"] == pytest.approx(20.0 / 180.0, rel=0.01)
        assert result["data_quality"] == DataQuality.GOOD
    
    def test_unavailable_data(self):
        """Test handling of unavailable order flow data."""
        validator = OrderFlowValidator()
        order_flow = {"symbol": "BTCUSDT"}  # missing bid/ask
        
        result = validator.validate(order_flow)
        assert result["status"] == "UNAVAILABLE"
        assert result["data_quality"] == DataQuality.UNAVAILABLE
    
    def test_negative_bid_volume_rejected(self):
        """Test rejection of negative bid volume."""
        validator = OrderFlowValidator()
        order_flow = {
            "symbol": "BTCUSDT",
            "bid_volume": -100.0,
            "ask_volume": 80.0
        }
        with pytest.raises(ValidationError, match="negative"):
            validator.validate(order_flow)
    
    def test_zero_volumes(self):
        """Test handling of zero bid/ask volumes."""
        validator = OrderFlowValidator()
        order_flow = {
            "symbol": "BTCUSDT",
            "bid_volume": 0.0,
            "ask_volume": 0.0
        }
        result = validator.validate(order_flow)
        assert result["delta"] == 0.0
        assert result["imbalance"] == 0.0


class TestDataQualityClassification:
    """Test data quality classification across validators."""
    
    def test_good_quality_propagation(self):
        """Test that GOOD quality is set for valid data."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": 50000.0,
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": 100.5,
        }
        result = validator.validate(candle)
        assert result.data_quality == DataQuality.GOOD
    
    def test_invalid_quality_propagation(self):
        """Test that INVALID quality is set for bad data."""
        validator = OHLCVValidator()
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": time.time(),
            "open": -50000.0,  # negative price
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": 100.5,
        }
        result = validator.validate(candle)
        assert result.data_quality == DataQuality.INVALID
    
    def test_stale_quality_propagation(self):
        """Test that STALE quality is set for old data."""
        validator = OHLCVValidator(max_staleness_seconds=60)
        old_timestamp = time.time() - 120
        candle = {
            "symbol": "BTCUSDT",
            "timestamp": old_timestamp,
            "open": 50000.0,
            "high": 51000.0,
            "low": 49500.0,
            "close": 50500.0,
            "volume": 100.5,
        }
        result = validator.validate(candle)
        assert result.data_quality == DataQuality.STALE
