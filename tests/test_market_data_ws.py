import pytest
import time
import json
from market_data.binance_futures_ws import BinanceFuturesWSClient
from models.domain import Provenance
from core.safety import SafetyViolationError


def test_ws_client_initialization_safety():
    client = BinanceFuturesWSClient(symbol="BTCUSDT", timeframe="15m")
    assert client.symbol == "BTCUSDT"
    assert "wss://fstream.binance.com/ws/btcusdt@kline_15m" in client.ws_url
    assert client.is_data_stale() is True


def test_ws_client_blocked_unsafe_endpoint():
    with pytest.raises(SafetyViolationError):
        BinanceFuturesWSClient(
            symbol="BTCUSDT",
            base_ws_url="wss://api.binance.com/ws"
        )


def test_ws_parse_valid_payload():
    client = BinanceFuturesWSClient(symbol="BTCUSDT", timeframe="15m")
    raw_payload = json.dumps({
        "e": "kline",
        "E": 1700000010000,
        "s": "BTCUSDT",
        "k": {
            "t": 1700000000000,
            "T": 1700000899999,
            "s": "BTCUSDT",
            "i": "15m",
            "o": "50000.00",
            "c": "50500.00",
            "h": "50600.00",
            "l": "49900.00",
            "v": "12.345",
            "x": True
        }
    })
    
    result = client.parse_kline_payload(raw_payload)
    assert result is not None
    candle, is_closed = result
    
    assert candle.symbol == "BTCUSDT"
    assert candle.open == 50000.0
    assert candle.close == 50500.0
    assert candle.high == 50600.0
    assert candle.low == 49900.0
    assert candle.volume == 12.345
    assert candle.provenance == Provenance.REAL
    assert is_closed is True


def test_ws_parse_malformed_payload():
    client = BinanceFuturesWSClient(symbol="BTCUSDT", timeframe="15m")
    
    # Missing 'k' key
    res1 = client.parse_kline_payload(json.dumps({"ping": 123}))
    assert res1 is None
    
    # Non-json string
    res2 = client.parse_kline_payload("INVALID_GARBAGE_PAYLOAD")
    assert res2 is None


def test_ws_stale_detection():
    client = BinanceFuturesWSClient(symbol="BTCUSDT", stale_threshold_sec=2.0)
    assert client.is_data_stale() is True
    
    client.last_message_ts = time.time()
    assert client.is_data_stale() is False
    
    client.last_message_ts = time.time() - 3.0
    assert client.is_data_stale() is True
