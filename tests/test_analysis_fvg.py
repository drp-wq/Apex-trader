import pytest
from models.domain import Candle
from analysis.fvg import FVGEngine


def test_bullish_fvg_detection_and_mitigation():
    engine = FVGEngine()
    candles = [
        Candle("BTCUSDT", 10.0, 100, 102, 99, 101, 10),  # c0: high=102
        Candle("BTCUSDT", 20.0, 101, 115, 101, 114, 25), # c1: big candle
        Candle("BTCUSDT", 30.0, 114, 120, 106, 118, 15), # c2: low=106 -> Gap [102, 106]
        Candle("BTCUSDT", 40.0, 118, 119, 101, 103, 10), # post: dips to 101 -> Mitigated
    ]
    fvgs = engine.detect_fvgs(candles)
    assert len(fvgs) == 1
    assert fvgs[0].is_bullish is True
    assert fvgs[0].bottom == 102.0
    assert fvgs[0].top == 106.0
    assert fvgs[0].mitigated is True


def test_bearish_fvg_unmitigated():
    engine = FVGEngine()
    candles = [
        Candle("BTCUSDT", 10.0, 120, 121, 118, 119, 10), # c0: low=118
        Candle("BTCUSDT", 20.0, 119, 119, 105, 106, 25), # c1: big down
        Candle("BTCUSDT", 30.0, 106, 112, 104, 105, 15), # c2: high=112 -> Gap [112, 118]
    ]
    unmitigated = engine.get_unmitigated_fvgs(candles)
    assert len(unmitigated) == 1
    assert unmitigated[0].is_bullish is False
    assert unmitigated[0].bottom == 112.0
    assert unmitigated[0].top == 118.0
    assert unmitigated[0].mitigated is False
