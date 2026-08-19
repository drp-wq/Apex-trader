import pytest
from models.domain import Candle
from analysis.order_blocks import OrderBlockEngine


def test_bullish_order_block():
    engine = OrderBlockEngine(displacement_multiplier=1.2)
    candles = [
        Candle("BTCUSDT", 10.0, 100, 101, 98, 99, 10),   # Bearish setup bar: top=101, bottom=98
        Candle("BTCUSDT", 20.0, 99, 115, 99, 114, 40),   # Strong Bullish expansion
        Candle("BTCUSDT", 30.0, 114, 118, 112, 116, 15),
    ]
    obs = engine.detect_order_blocks(candles)
    assert len(obs) == 1
    assert obs[0].is_bullish is True
    assert obs[0].top == 101.0
    assert obs[0].bottom == 98.0
    assert obs[0].mitigated is False


def test_bearish_order_block():
    engine = OrderBlockEngine(displacement_multiplier=1.2)
    candles = [
        Candle("BTCUSDT", 10.0, 100, 104, 99, 103, 10),  # Bullish setup bar: top=104, bottom=99
        Candle("BTCUSDT", 20.0, 103, 103, 85, 87, 40),   # Strong Bearish expansion
        Candle("BTCUSDT", 30.0, 87, 89, 84, 85, 15),
    ]
    obs = engine.detect_order_blocks(candles)
    assert len(obs) == 1
    assert obs[0].is_bullish is False
    assert obs[0].top == 104.0
    assert obs[0].bottom == 99.0
