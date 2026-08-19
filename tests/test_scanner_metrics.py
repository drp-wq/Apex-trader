import pytest
from models.domain import Candle, Provenance
from scanner.oi_engine import OIEngine
from scanner.rvol_engine import RVOLEngine
from scanner.market_metrics import MarketMetricsEngine


def test_oi_engine_spike_detection():
    engine = OIEngine(spike_threshold_pct=5.0)
    metrics = engine.analyze([1000.0, 1060.0])
    assert metrics.current_oi == 1060.0
    assert metrics.previous_oi == 1000.0
    assert metrics.oi_change == 60.0
    assert metrics.oi_change_pct == 6.0
    assert metrics.is_spike is True


def test_oi_engine_empty_and_single_entry():
    engine = OIEngine()
    empty = engine.analyze([])
    assert empty.current_oi == 0.0
    assert empty.is_spike is False

    single = engine.analyze([500.0])
    assert single.current_oi == 500.0
    assert single.oi_change == 0.0


def test_rvol_engine_standard_calculation():
    engine = RVOLEngine(lookback_periods=5, high_volume_threshold=2.0)
    # Baseline average for prior 5 bars: (10+10+10+10+10) / 5 = 10.0
    # Current volume: 25.0 -> RVOL = 2.5
    vol_history = [10.0, 10.0, 10.0, 10.0, 10.0, 25.0]
    metrics = engine.calculate(vol_history)
    assert metrics.current_volume == 25.0
    assert metrics.baseline_average_volume == 10.0
    assert metrics.rvol == 2.5
    assert metrics.is_high_volume is True


def test_rvol_engine_zero_volume():
    engine = RVOLEngine()
    metrics = engine.calculate([0.0, 0.0, 0.0])
    assert metrics.rvol == 0.0
    assert metrics.is_high_volume is False


def test_market_metrics_snapshot_aggregation():
    engine = MarketMetricsEngine(min_rvol_favorable=1.5)
    candles = [
        Candle("BTCUSDT", 100.0, 50000.0, 50200.0, 49900.0, 50100.0, 10.0, provenance=Provenance.PAPER),
        Candle("BTCUSDT", 200.0, 50100.0, 50600.0, 50000.0, 50500.0, 10.0, provenance=Provenance.PAPER),
        Candle("BTCUSDT", 300.0, 50500.0, 51000.0, 50400.0, 50900.0, 20.0, provenance=Provenance.PAPER),
    ]
    oi_data = [50000.0, 52000.0, 53500.0]

    snapshot = engine.compute_snapshot(candles, oi_data)
    assert snapshot.symbol == "BTCUSDT"
    assert snapshot.latest_price == 50900.0
    assert snapshot.price_change_pct > 0.0
    assert snapshot.rvol_metrics.rvol == 2.0
    assert snapshot.is_favorable_momentum is True
