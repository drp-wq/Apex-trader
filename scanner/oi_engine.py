"""
Open Interest Analysis Engine.
Calculates deterministic OI changes, percentage growth, and spike detection.
"""
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class OIMetrics:
    current_oi: float
    previous_oi: float
    oi_change: float
    oi_change_pct: float
    is_spike: bool


class OIEngine:
    def __init__(self, spike_threshold_pct: float = 5.0):
        self.spike_threshold_pct = spike_threshold_pct

    def analyze(self, oi_series: List[float]) -> OIMetrics:
        """
        Analyzes an ordered time series of open interest values (oldest to newest).
        """
        if not oi_series:
            return OIMetrics(
                current_oi=0.0,
                previous_oi=0.0,
                oi_change=0.0,
                oi_change_pct=0.0,
                is_spike=False
            )

        if len(oi_series) == 1:
            return OIMetrics(
                current_oi=float(oi_series[0]),
                previous_oi=float(oi_series[0]),
                oi_change=0.0,
                oi_change_pct=0.0,
                is_spike=False
            )

        current = float(oi_series[-1])
        previous = float(oi_series[-2])

        if previous <= 0.0:
            change = current - previous
            return OIMetrics(
                current_oi=current,
                previous_oi=previous,
                oi_change=change,
                oi_change_pct=0.0,
                is_spike=False
            )

        change = current - previous
        change_pct = round((change / previous) * 100.0, 4)
        is_spike = change_pct >= self.spike_threshold_pct

        return OIMetrics(
            current_oi=round(current, 4),
            previous_oi=round(previous, 4),
            oi_change=round(change, 4),
            oi_change_pct=change_pct,
            is_spike=is_spike
        )
