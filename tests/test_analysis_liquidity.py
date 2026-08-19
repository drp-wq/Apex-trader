import pytest
from models.domain import Candle
from analysis.liquidity import LiquidityEngine
from analysis.models import LiquidityType


def test_liquidity_bsl_and_ssl():
    engine = LiquidityEngine(swing_lookback=1)
    candles = [
        Candle("BTCUSDT", 10.0, 100, 102, 98, 100, 10),
        Candle("BTCUSDT", 20.0, 100, 110, 99, 108, 10),  # BSL @ 110
        Candle("BTCUSDT", 30.0, 108, 105, 92, 95, 10),   # SSL @ 92
        Candle("BTCUSDT", 40.0, 95, 100, 94, 98, 10),
    ]
    pools = engine.detect_liquidity_pools(candles)
    types = [p.level_type for p in pools]
    assert LiquidityType.BSL in types
    assert LiquidityType.SSL in types


def test_liquidity_sweep():
    engine = LiquidityEngine(swing_lookback=1)
    candles = [
        Candle("BTCUSDT", 10.0, 100, 102, 98, 100, 10),
        Candle("BTCUSDT", 20.0, 100, 110, 99, 108, 10),  # BSL @ 110
        Candle("BTCUSDT", 30.0, 108, 105, 101, 104, 10),
        Candle("BTCUSDT", 40.0, 104, 115, 102, 105, 20),  # Sweeps 110 high
    ]
    sweeps = engine.detect_sweeps(candles)
    assert len(sweeps) >= 1
    assert sweeps[0].level_type == LiquidityType.BSL
    assert sweeps[0].swept is True
