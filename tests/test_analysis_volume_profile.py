import pytest
from models.domain import Candle
from analysis.volume_profile import VolumeProfileEngine


def test_volume_profile_poc_and_value_area():
    engine = VolumeProfileEngine(num_bins=10, value_area_pct=0.70)
    candles = [
        Candle("BTCUSDT", 10.0, 100, 102, 98, 100, 10.0),
        Candle("BTCUSDT", 20.0, 100, 102, 98, 101, 50.0),  # Heavy concentration around ~100
        Candle("BTCUSDT", 30.0, 101, 103, 99, 100, 40.0),
        Candle("BTCUSDT", 40.0, 100, 110, 100, 109, 5.0),  # Outlier light volume
    ]
    vp = engine.calculate(candles)
    assert vp.total_volume == 105.0
    assert 98.0 <= vp.poc <= 104.0
    assert vp.val <= vp.poc <= vp.vah


def test_volume_profile_empty():
    engine = VolumeProfileEngine()
    vp = engine.calculate([])
    assert vp.total_volume == 0.0
    assert vp.poc == 0.0
