import pytest
from models.domain import Candle, TrendState
from analysis.market_structure import MarketStructureEngine


def test_market_structure_bullish_progression():
    engine = MarketStructureEngine(left_bars=1, right_bars=1)
    candles = [
        Candle("BTCUSDT", 10.0, 100, 105, 95, 102, 10),
        Candle("BTCUSDT", 20.0, 102, 110, 101, 108, 10),  # Swing High @ 110
        Candle("BTCUSDT", 30.0, 108, 107, 100, 103, 10),
        Candle("BTCUSDT", 40.0, 103, 105, 98, 101, 10),   # Swing Low @ 98
        Candle("BTCUSDT", 50.0, 101, 115, 100, 114, 20),  # Breaks 110 -> BOS / CHOCH
    ]
    res = engine.analyze(candles)
    assert res.trend == TrendState.BULLISH
    assert len(res.breaks) >= 1
    assert res.breaks[-1].direction == "BULLISH"


def test_market_structure_bearish_progression():
    engine = MarketStructureEngine(left_bars=1, right_bars=1)
    candles = [
        Candle("BTCUSDT", 10.0, 100, 105, 95, 98, 10),
        Candle("BTCUSDT", 20.0, 98, 99, 90, 92, 10),     # Swing Low @ 90
        Candle("BTCUSDT", 30.0, 92, 96, 91, 95, 10),     # Swing High @ 96
        Candle("BTCUSDT", 40.0, 95, 96, 93, 94, 10),
        Candle("BTCUSDT", 50.0, 94, 94, 85, 86, 20),     # Breaks 90 -> Bearish
    ]
    res = engine.analyze(candles)
    assert res.trend == TrendState.BEARISH
    assert len(res.breaks) >= 1
    assert res.breaks[-1].direction == "BEARISH"


def test_market_structure_empty():
    engine = MarketStructureEngine()
    res = engine.analyze([])
    assert res.trend == TrendState.RANGING
    assert res.swing_highs == []
