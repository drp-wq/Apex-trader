from typing import List

def compute_oi_delta(oi_series: List[float]) -> float:
    if len(oi_series) < 2:
        return 0.0
    return round(((oi_series[-1] - oi_series[-2]) / oi_series[-2]) * 100.0, 2)

def is_oi_spike(oi_series: List[float], threshold_pct: float = 5.0) -> bool:
    delta = compute_oi_delta(oi_series)
    return delta >= threshold_pct

def test_oi_delta_calculation():
    series = [100000.0, 105000.0]
    assert compute_oi_delta(series) == 5.0

def test_oi_spike_detection():
    series = [100000.0, 108000.0]
    assert is_oi_spike(series, 5.0) is True

def test_oi_normalization():
    series = [100000.0, 95000.0]
    assert compute_oi_delta(series) == -5.0

def test_oi_empty_feed():
    assert compute_oi_delta([]) == 0.0
    assert compute_oi_delta([100000.0]) == 0.0
